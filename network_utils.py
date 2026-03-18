import io
import os
import ssl
import sys
import urllib.error
import urllib.request


_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
_BUNDLED_CA_BUNDLE = os.path.join(_PLUGIN_DIR, "certs", "cacert.pem")
_COMMON_CA_FILENAMES = (
    "cacert.pem",
    "ca-bundle.crt",
    "ca-bundle.trust.crt",
    "cert.pem",
)


class MemoryResponse(io.BytesIO):
    def __init__(self, data, url=None, status=None, headers=None):
        super().__init__(data)
        self.url = url
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def _existing_file(path):
    if path and os.path.exists(path):
        return path
    return None


def _candidate_ca_directories():
    paths = []

    for env_var in ("QGIS_PREFIX_PATH", "OSGEO4W_ROOT"):
        root = os.environ.get(env_var)
        if not root:
            continue
        paths.extend(
            [
                root,
                os.path.join(root, "apps", "Python"),
                os.path.join(root, "apps", "Python311"),
                os.path.join(root, "apps", "Python312"),
                os.path.join(root, "apps", "qgis"),
                os.path.join(root, "apps", "qgis-ltr"),
                os.path.join(root, "bin"),
            ]
        )

    paths.extend(
        [
            sys.prefix,
            os.path.dirname(sys.executable),
            os.path.join(sys.prefix, "Lib", "site-packages", "certifi"),
            os.path.join(sys.prefix, "Library", "bin"),
        ]
    )

    try:
        from qgis.core import QgsApplication

        for qgis_root in (QgsApplication.prefixPath(), QgsApplication.pkgDataPath()):
            if qgis_root:
                paths.extend(
                    [
                        qgis_root,
                        os.path.join(qgis_root, "bin"),
                        os.path.join(qgis_root, "resources"),
                        os.path.join(qgis_root, "resources", "ssl"),
                        os.path.join(qgis_root, "resources", "ssl", "certs"),
                        os.path.join(qgis_root, "certs"),
                    ]
                )
    except Exception:
        pass

    seen = set()
    for path in paths:
        normalized = os.path.normpath(path)
        if normalized in seen or not os.path.isdir(normalized):
            continue
        seen.add(normalized)
        yield normalized


def _ca_bundle_path():
    for env_var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        candidate = os.environ.get(env_var)
        existing = _existing_file(candidate)
        if existing:
            return existing

    existing = _existing_file(_BUNDLED_CA_BUNDLE)
    if existing:
        return existing

    try:
        import certifi

        existing = _existing_file(certifi.where())
        if existing:
            return existing
    except Exception:
        pass

    verify_paths = ssl.get_default_verify_paths()
    for candidate in (verify_paths.cafile, verify_paths.openssl_cafile):
        existing = _existing_file(candidate)
        if existing:
            return existing

    for directory in _candidate_ca_directories():
        for filename in _COMMON_CA_FILENAMES:
            existing = _existing_file(os.path.join(directory, filename))
            if existing:
                return existing

    return None


def create_ssl_context():
    ca_bundle = _ca_bundle_path()
    if ca_bundle:
        return ssl.create_default_context(cafile=ca_bundle)
    return ssl.create_default_context()


def _urlopen_with_qgis(url, timeout=40):
    from qgis.PyQt.QtCore import QEventLoop, QTimer, QUrl
    from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest
    from qgis.core import QgsNetworkAccessManager

    request = QNetworkRequest(QUrl(url))
    reply = QgsNetworkAccessManager.instance().get(request)

    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    reply.finished.connect(loop.quit)
    timer.start(int(timeout * 1000))
    loop.exec_()

    if timer.isActive():
        timer.stop()
    else:
        reply.abort()
        reply.deleteLater()
        raise urllib.error.URLError(f"timed out after {timeout} seconds")

    status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
    reason = reply.attribute(QNetworkRequest.HttpReasonPhraseAttribute)
    final_url = reply.url().toString()
    headers = {}
    for raw_header in reply.rawHeaderList():
        headers[bytes(raw_header).decode("utf-8", errors="ignore")] = bytes(
            reply.rawHeader(raw_header)
        ).decode("utf-8", errors="ignore")

    if reply.error() != QNetworkReply.NoError:
        body = bytes(reply.readAll())
        message = reply.errorString() or str(reason or "network error")
        reply.deleteLater()
        if status and int(status) >= 400:
            raise urllib.error.HTTPError(final_url, int(status), message, headers, io.BytesIO(body))
        raise urllib.error.URLError(message)

    body = bytes(reply.readAll())
    reply.deleteLater()

    if status and int(status) >= 400:
        raise urllib.error.HTTPError(final_url, int(status), str(reason or "HTTP error"), headers, io.BytesIO(body))

    return MemoryResponse(body, url=final_url, status=int(status) if status else None, headers=headers)


def urlopen(url, timeout=40, **kwargs):
    kwargs.pop("context", None)
    try:
        return _urlopen_with_qgis(url, timeout=timeout)
    except ImportError:
        context = create_ssl_context()
        return urllib.request.urlopen(url, context=context, timeout=timeout, **kwargs)


def describe_ssl_context():
    ca_bundle = _ca_bundle_path()
    backend = "Qt/QGIS" if "qgis" in sys.modules else "Python ssl"
    if ca_bundle:
        return f"Backend de rede: {backend}\nCA bundle em uso: {ca_bundle}"
    return f"Backend de rede: {backend}\nNenhum CA bundle foi encontrado no ambiente."

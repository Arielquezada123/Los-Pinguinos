from whitenoise.storage import CompressedManifestStaticFilesStorage

class RobustStaticFilesStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False
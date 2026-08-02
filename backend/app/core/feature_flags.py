import os
import logging

logger = logging.getLogger("app.startup")


class FeatureFlags:
    """Manages environment-driven runtime feature flags.
    
    Allows enabling/disabling features without code changes.
    """
    
    @property
    def AI_PROVIDERS(self) -> bool:
        return self._get_flag("FEATURE_AI_PROVIDERS", True)

    @property
    def EXPERIMENTAL_ENDPOINTS(self) -> bool:
        return self._get_flag("FEATURE_EXPERIMENTAL_ENDPOINTS", False)

    @property
    def BACKGROUND_WORKERS(self) -> bool:
        return self._get_flag("FEATURE_BACKGROUND_WORKERS", True)

    @property
    def METRICS(self) -> bool:
        return self._get_flag("FEATURE_METRICS", True)

    @property
    def CACHE(self) -> bool:
        return self._get_flag("FEATURE_CACHE", True)

    @property
    def COMPRESSION(self) -> bool:
        return self._get_flag("FEATURE_COMPRESSION", True)

    def _get_flag(self, env_key: str, default: bool) -> bool:
        val = os.getenv(env_key)
        if val is None:
            return default
        # Return boolean evaluation of env value
        return val.lower() in ("true", "1", "yes", "on", "t")

    def get_all_flags(self) -> dict:
        """Returns a snapshot of all feature flag evaluations."""
        return {
            "FEATURE_AI_PROVIDERS": self.AI_PROVIDERS,
            "FEATURE_EXPERIMENTAL_ENDPOINTS": self.EXPERIMENTAL_ENDPOINTS,
            "FEATURE_BACKGROUND_WORKERS": self.BACKGROUND_WORKERS,
            "FEATURE_METRICS": self.METRICS,
            "FEATURE_CACHE": self.CACHE,
            "FEATURE_COMPRESSION": self.COMPRESSION
        }


# Global feature flags manager singleton
feature_flags = FeatureFlags()

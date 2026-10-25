"""Load ML dependencies on demand so model errors do not prevent account/game access."""
import threading
class LazyModelManager:
    def __init__(self):
        self.lock=threading.RLock()
        self._manager=None
        self.last_error=None
    def _load_runtime(self):
        if self._manager is None:
            try:
                from .model_manager import model_manager
                self._manager=model_manager
                self._manager.lock=self.lock
            except Exception as exc:
                self.last_error=f'Model runtime unavailable: {exc}. Start the backend using the project .venv and install backend/requirements.txt.'
                raise RuntimeError(self.last_error) from exc
        return self._manager
    def ensure_loaded(self):
        with self.lock:
            try:
                self._load_runtime().ensure_loaded()
                self.last_error=None
            except Exception as exc:
                self.last_error=str(exc)
                raise
    def predict(self,*args,**kwargs):
        return self._load_runtime().predict(*args,**kwargs)
    def __getattr__(self,name):
        if self._manager is not None: return getattr(self._manager,name)
        defaults={'checkpoint_sha256':None,'checkpoint_epoch':None,'is_custom_checkpoint_loaded':False,'device':'not loaded','signature':None}
        if name in defaults: return defaults[name]
        raise AttributeError(name)
model_manager=LazyModelManager()

from .pytorch_kr import PyTorchKRSource
from .gpters import GPTERSNewsSource
from .raindrop import RaindropSource
from .youtube import YouTubeSource
from .obsidian import ObsidianSource

def get_source(source_name):
    if source_name == "pytorch_kr":
        return PyTorchKRSource
    elif source_name == "gpters":
        return GPTERSNewsSource
    elif source_name == "raindrop":
        return RaindropSource
    elif source_name == "youtube":
        return YouTubeSource
    elif source_name == "obsidian":
        return ObsidianSource
    else:
        raise ValueError(f"Unknown source: {source_name}")

import swebench.harness.extractor.extractor_base as extractor_base

class FullGenExtractor(extractor_base.ExtractorBase):
    def __init__(self):
        super().__init__()

    def extract(self, data: str) -> str:
        pass

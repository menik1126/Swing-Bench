from abc import abstractmethod


class ExtractorBase:
    @abstractmethod
    def __init__(self):
        raise NotImplementedError

    @abstractmethod
    def extract(self, data: str) -> str:
        raise NotImplementedError


if __name__ == "__main__":
  pass
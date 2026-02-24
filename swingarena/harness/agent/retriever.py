from abc import abstractmethod
from pathlib import Path
from swingarena.harness.constants.swing_constants import SwingbenchInstance
from swingarena.harness.agent.swing_search_index import search_instance


class Retriever:
    @abstractmethod
    def __init__(self):
        raise NotImplementedError("Retriever is not implemented yet.")

    @abstractmethod
    def retrieve(self, instance: SwingbenchInstance):
        raise NotImplementedError("Retrieve is not implemented yet.")

class BM25DiskRetriever(Retriever):
    def __init__(self, index_dir: str, document_encoding_style: str = "file_name_and_contents"):
        self.index_dir = Path(index_dir)
        self.document_encoding_style = document_encoding_style

    def retrieve(self, instance: SwingbenchInstance, src_folder: str, k: int = 1):
        results = search_instance(
            instance,
            self.index_dir,
            src_folder,
            self.document_encoding_style,
            k=k
        )
        # TODO(wdxu): need some reduce strategies
        
        return results


if __name__ == "__main__":
    import swing_utils

    retriever = BM25DiskRetriever(index_dir="/mnt/Data/wdxu/github/Swing-Bench/tmpdata/indexes")
    dataset_jsonl_path = '/mnt/Data/wdxu/github/Swing-Bench/tmpdata/dataset.json'
    dataset = swing_utils.load_swingbench_dataset(dataset_jsonl_path)
    
    for instance in dataset:
        results = retriever.retrieve(instance)
        print(results)

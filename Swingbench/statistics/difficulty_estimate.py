from utils import process_instances_parallel, build_dataset
from utils import annotated_jsonl_dir


def main():
    dataset = build_dataset()
    annoted_language = "cpp"
    output_file = annotated_jsonl_dir / f"{annoted_language}.jsonl"
    instances = dataset[annoted_language]
    api_key = ""
    base_url = ""
    model = ""

    process_instances_parallel(
        instances, output_file, api_key, base_url, model, num_workers=10, max_attempts=3, need_chunk=False, chunk_type="block", language=annoted_language, max_chunk_num=3
    )

    process_instances_parallel(
        instances, output_file, api_key, base_url, model, num_workers=10, max_attempts=3, need_chunk=True, chunk_type="block", language=annoted_language, max_chunk_num=3
    )


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-

import json
import logging
from pathlib import Path
import subprocess

from argparse import ArgumentParser
from pyserini.search.lucene import LuceneSearcher
from tqdm import tqdm
from swingarena.harness.constants.swing_constants import SwingbenchInstance
from swingarena.prepare.swing_build_index import build_repo_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def search_instance(
    instance: SwingbenchInstance,
    index_root: Path,
    src_folder: Path,
    document_encoding_style: str,
    k: int = 20
) -> dict:
    repo = instance.repo
    commit = instance.base_commit
    query = instance.problem_statement + " " + instance.hints_text
    
    index_path = (
        index_root / 
        repo.replace('/', '__') / 
        document_encoding_style /
        commit /
        "index"
    )
    
    if not index_path.exists():
        logger.error(f"Index at {index_path} not found for {repo} at commit {commit}. Building index...")
        python = subprocess.run("which python", shell=True, capture_output=True)
        python = python.stdout.decode("utf-8").strip()
        print(f"Build repo index: repo:{repo}, commit:{commit}, index_root:{index_root}, repo_root_dir:{src_folder}, document_encoding_style:{document_encoding_style}")
        build_repo_index(
            repo=repo,
            commits=(commit,),
            root_dir=index_root,
            repo_root_dir=src_folder,
            document_encoding_style=document_encoding_style,
            python=python,
            github_base_url="https://github.com",
        )
    try:
        searcher = LuceneSearcher(index_path.as_posix())
        cutoff = len(query)
        print(f"[DEBUG] cutoff: {cutoff}")
        while True:
            try:
                hits = searcher.search(
                    query[:cutoff],
                    k=k,
                    remove_dups=True,
                )
                print(f"[DEBUG] hits: {hits}")
                break
            except Exception as e:
                if "maxClauseCount" in str(e):
                    cutoff = int(round(cutoff * 0.8))
                    continue
                else:
                    raise e
        
        results = {
            "instance_id": instance.instance_id,
            "hits": []
        }
        
        for hit in hits:
            raw_doc = json.loads(searcher.doc(hit.docid).raw())
            results["hits"].append({
                "docid": hit.docid,
                "score": hit.score,
                "contents": raw_doc.get("contents", ""),
                "relative_path": raw_doc.get("id", "")
            })
            
        return results
        
    except Exception as e:
        logger.error(f"Search failed for instance {instance.instance_id}")
        logger.error(str(e))
        return None


def main(debug: bool = False):
    """_summary_

    Returns:
        dict: {instance_id: retrieved results}
        
        JSONL format:
        {
            "instance_id": instance_id,
            "hits": [
                {
                    "docid": docid (path/file.ext),
                    "score": score,
                    "contents": contents,
                    "relative_path": relative_path
                },
                ...
            ]
        }
    """
    parser = ArgumentParser()
    parser.add_argument("--instances_file", type=str, required=True,
                      help="Path to the dataset.json file")
    parser.add_argument("--index_dir", type=str, required=True,
                      help="Root directory containing indexes")
    parser.add_argument("--document_encoding_style",
                      choices=["file_name_and_contents", "file_name_and_documentation"],
                      default="file_name_and_contents")
    parser.add_argument("--output_file_for_debug", type=str, default=None,
                      help="Output file to store search results")
    args = parser.parse_args()
    
    instances = []
    with open(args.instances_file) as f:
        for line in f:
            instances.append(SwingbenchInstance(**json.loads(line)))
    
    index_root = Path(args.index_dir)
    if debug:
        with open(args.output_file_for_debug, "w") as out_f:
            for instance in tqdm(instances, desc="Searching"):
                results = search_instance(
                    instance,
                    index_root,
                    args.document_encoding_style
                )
                if results:
                        print(json.dumps(results), flush=True)
    else:
        results_dir = {}
        for instance in tqdm(instances, desc="Searching"):
            results = search_instance(
                instance,
                index_root,
                args.document_encoding_style
            )
            if results:
                results_dir[instance.instance_id] = results
        return results_dir


if __name__ == "__main__":
    """
    python swing_search_index.py \
        --instances_file /mnt/Data/wdxu/github/Swing-Bench/tmpdata/dataset.json \
        --index_dir /mnt/Data/wdxu/github/Swing-Bench/tmpdata/indexes \
        --document_encoding_style file_name_and_contents \
        --output_file_for_debug results.jsonl
    """
    main(debug=True)
    # result = main(debug=False)
    # for each in result:
    #     print(each, result[each])

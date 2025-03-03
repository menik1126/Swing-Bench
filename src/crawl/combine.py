import jsonlines
with jsonlines.open("repos/crateio.jsonl", "r") as f:
    ds = list(f)
with jsonlines.open("repos/awesome-rust.jsonl", "r") as f:
    ds.extend(list(f))
print(len(ds))
ds = {item['url']: item for item in ds}.values()
results = []
for d in ds:
    if d['stars'] >= 5 and d['issues'] >= 3:
        results.append(d)
print(len(results))
with jsonlines.open("rust-repos-awesome-crateio.jsonl", "w") as f:
    f.write_all(results)
from owid.catalog import search, fetch

results = search("corruption")
items = results.to_frame()

# CPI laden
url = items.iloc[0]['url']
print(f"Lade: {url}")

data = fetch(url)
print(type(data))
print(data)
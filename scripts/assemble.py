import sys
src, data, out = sys.argv[1:4]
page = open(src, encoding="utf-8").read()
blob = open(data, encoding="utf-8").read().replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
assert "/*__DATA__*/" in page
open(out, "w", encoding="utf-8").write(page.replace("/*__DATA__*/", blob))
print("wrote", out, len(page) + len(blob), "bytes")

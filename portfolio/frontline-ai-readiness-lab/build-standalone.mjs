// Builds standalone.html: one self-contained file that runs anywhere (email attachment,
// GitHub Pages, any static host). index.html is the source page; it has no <html>/<head>
// wrapper because the Claude artifact host adds one at publish time.
import { readFileSync, writeFileSync } from "node:fs";

const dir = new URL(".", import.meta.url);
const read = (f) => readFileSync(new URL(f, dir), "utf8");

let page = read("index.html");
for (const f of ["content.js", "app.js"]) {
  page = page.replace(`<script src="${f}"></script>`, () => `<script>\n${read(f)}\n</script>`);
}

const head =
  '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n' +
  '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n' +
  "<style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n" +
  "</head>\n<body>\n";

writeFileSync(new URL("standalone.html", dir), head + page + "\n</body>\n</html>\n");
console.log("standalone.html written");

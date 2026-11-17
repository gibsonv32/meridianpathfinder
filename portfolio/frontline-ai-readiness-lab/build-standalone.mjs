// Builds the self-contained version of the app for hosting outside Claude.
//   standalone.html   one file to email or open directly
//   site/index.html   the same file, named for static hosts (GitHub Pages, Netlify, any web server)
// index.html is the source page; it has no <html>/<head> wrapper because the Claude
// artifact host adds one at publish time.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const dir = new URL(".", import.meta.url);
const read = (f) => readFileSync(new URL(f, dir), "utf8");

let page = read("index.html");
for (const f of ["content.js", "app.js"]) {
  page = page.replace(`<script src="${f}"></script>`, () => `<script>\n${read(f)}\n</script>`);
}

const title = "Frontline AI Readiness Lab";
const description =
  "An interactive 15-minute AI readiness sprint for contact center teams: adaptive lessons, a scored simulation, coaching and an adoption dashboard. Work sample by Vincent Gibson, built on synthetic data.";

const head =
  '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n' +
  '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n' +
  `<title>${title}</title>\n` +
  `<meta name="description" content="${description}">\n` +
  `<meta property="og:type" content="website">\n` +
  `<meta property="og:title" content="${title}">\n` +
  `<meta property="og:description" content="${description}">\n` +
  "<style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n" +
  "</head>\n<body>\n";

const out = head + page + "\n</body>\n</html>\n";
writeFileSync(new URL("standalone.html", dir), out);
mkdirSync(new URL("site/", dir), { recursive: true });
writeFileSync(new URL("site/index.html", dir), out);
console.log("standalone.html and site/index.html written");

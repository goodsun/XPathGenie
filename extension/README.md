# 🐒 XPathAbu — DomCatcher

![Abu Character Design](docs/abu_charsheet.jpg)

**The street-smart monkey who snatches XPaths right off the DOM.**

XPathAbu is a Chrome extension and the newest member of the [XPathGenie](https://github.com/goodsun/XPathGenie) family. Click any element on a page, get its XPath instantly, and refine it with an interactive breadcrumb navigator.

## Features

- **🎯 Click to Capture** — Click any DOM element to grab its XPath. `<a>` tags automatically append `/@href`.
- **🍞 Breadcrumb Navigation** — Visual path display parsed from the XPath string. Click to navigate up, **Shift+click** to trim from `//`.
- **🔴 Index Badges** — `div[5]` shows as `div` with a red `5` badge. Click the badge to remove the index and select all matches.
- **📋 Copy XPath** — One-click copy of the current XPath (including manual edits).
- **✏️ Live Edit** — Edit the XPath directly and see results update in real-time (300ms debounce).
- **🔍 Multi-match** — When an XPath matches multiple elements, all results are listed and highlighted (purple for first, red for additional matches).
- **🖱️ Drag & Resize** — Drag the panel by the header, resize from the bottom-right grip.
- **👁️ Inspect Toggle** — ON/OFF to switch between inspect mode and normal page interaction.

## XPathGenie Family

| Tool | Character | Role |
|------|-----------|------|
| **Genie** 🧞 | Lamp Spirit | AI-powered XPath generation engine |
| **Jasmine** 🌸 | Princess | Interactive UI & section selection |
| **Aladdin** 🔮 | Hero | Multi-page analysis & validation |
| **Abu** 🐒 | Gangster Monkey | DOM element catcher (this extension) |

## Install

1. Clone or download this repo
2. Open `chrome://extensions/`
3. Enable **Developer mode**
4. Click **Load unpacked** → select the `extension/` folder
5. Click the Abu icon in the toolbar to activate on any page

## Usage

1. **Click the Abu icon** in Chrome toolbar → panel appears
2. **Hover** over elements → purple highlight shows boundaries
3. **Click** an element → XPath appears in the input field
4. **Edit** the XPath manually or use **breadcrumbs** to navigate
5. **Shift+click** a breadcrumb → trims XPath to start from that element (`//`)
6. **Click a red index badge** → removes `[n]` to match all siblings
7. **Copy XPath** → clipboard ready for your scraper

## Name

**Abu** = Aladdin's monkey companion + **Abuse** (as in DOM abuse). A small, mischievous sidekick who snatches data right off the page. 🐒

## License

MIT — Part of [XPathGenie](https://github.com/goodsun/XPathGenie)

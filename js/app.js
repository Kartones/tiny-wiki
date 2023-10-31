"use strict";

(function () {
  const timestampMark = Date.now();
  let pages = [];

  function splitPath(path) {
    const pathFragments = path.split("/");
    const page = pathFragments[pathFragments.length - 1].replace(".md", "");
    // max 2 levels of subfolders
    const section = pathFragments[1];
    const subSection = pathFragments.length > 3 ? pathFragments[2] : null;

    return [page, section, subSection];
  }

  async function readPagesList() {
    await Promise.all([fetch(`items.json?v=${timestampMark}`)]).then(
      async ([pagesData]) => {
        pages = await pagesData.json();
        pages = pages.filter((page) => page.endsWith(".md"));
        pages = pages.sort();

        document.getElementById("navigation").innerHTML = pages.reduce(
          (accumulator, pagePath, currentIndex, allPages) => {
            const [page, section, subSection] = splitPath(pagePath);
            let output = accumulator;
            let _,
              previousSection = "",
              previousSubSection = "";

            if (currentIndex > 0) {
              [_, previousSection, previousSubSection] = splitPath(
                allPages[currentIndex - 1]
              );
            }

            if (section !== previousSection) {
              output += `<li>${section.replace(".md", "")}</li>`;
            }
            if (subSection && subSection !== previousSubSection) {
              output += `<li>• ${subSection}</li>`;
            }

            return `${output}<li><a href="#" data-index=${currentIndex} class="${
              subSection ? "sub" : ""
            }">• ${page}</a></li>`;
          },
          ""
        );
      }
    );
  }

  async function loadPage(pagePath) {
    const [page, section, subSection] = splitPath(pagePath);

    await Promise.all([fetch(`${pagePath}?v=${timestampMark}`)])
      .then(async ([response]) => {
        if (response.ok) {
          let content = await response.text();

          // Adds the main page title (not present in the markdown files)
          document.getElementById("content").innerHTML = marked.parse(
            `# ${page}\n${content}`
          );

          loadHeadings(extractHeadings(content));

          window.scrollTo(0, 0);
        } else {
          document.getElementById("content").innerHTML = marked.parse(
            `# Error loading page '${section}/${
              subSection ? subSection + "/" : ""
            }${page}': 404`
          );
        }
      })
      .catch((error) => {
        document.getElementById("content").innerHTML = marked.parse(
          `# Error loading '${section}/${
            subSection ? "/" + subSection : ""
          }${page}': ${error}`
        );
      });
  }

  function loadHeadings(headings) {
    document.getElementById("headings").innerHTML = headings.reduce(
      (accumulator, heading) => {
        return `${accumulator}<li class="level-${
          heading.level
        }"><a href="#${headingId(heading.text)}">${heading.text}</a></li>`;
      },
      ""
    );
  }

  function extractHeadings(pageContent) {
    // exclude headings inside code blocks (by removing them)
    pageContent = pageContent.replace(/```[\s\S]*?```/g, "");
    const headings = pageContent.match(/^(#+)\s+(.+)$/gm);
    return headings.map((heading) => {
      const [_, level, text] = heading.match(/^(#+)\s+(.+)$/);
      return { level: level.length, text };
    });
  }

  function headingId(headingText) {
    return headingText
      .toLowerCase()
      .replace(/[^\w]+/g, "-")
      .replace(/-$/, "");
  }

  function loadTheme() {
    let mode = "light";
    let storedMode = localStorage.getItem("dark-mode");

    if (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    ) {
      mode = "dark";
    }
    if (storedMode) {
      mode = storedMode === "dark" ? "dark" : "light";
    }
    document.getElementsByTagName("html")[0].dataset.theme = mode;
  }

  const renderer = {
    image(href, title, text) {
      const escapedText = text.toLowerCase().replace(/[^\w]+/g, "-");
      const escapedTitle = (title ?? "").toLowerCase().replace(/[^\w]+/g, "-");

      if (href.match(/\.mp4$|\.webm$|\.ogg$/)) {
        return `<video controls><source src="${href}" type="video/mp4"></video>`;
      }

      return `<img src="${href}" title="${escapedTitle}" alt="${escapedText}" loading="lazy" />`;
    },
    heading(text, level) {
      return `<h${level} id="${headingId(text)}">${text}</h${level}>`;
    },
  };

  async function initialLoad() {
    loadTheme();

    document.getElementById("theme-switcher").addEventListener("click", () => {
      let mode =
        document.getElementsByTagName("html")[0].dataset.theme === "dark"
          ? "light"
          : "dark";
      document.getElementsByTagName("html")[0].dataset.theme = mode;
      localStorage.setItem("dark-mode", mode);
    });

    document.getElementById("navigation").addEventListener("click", (event) => {
      if (event.target.tagName === "A") {
        event.preventDefault();
        loadPage(pages[event.target.dataset.index]);
      }
    });

    marked.use({ renderer });

    await readPagesList();
    await loadPage(pages[0]);
  }

  initialLoad();
})();

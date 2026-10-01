import brandMark from "../components/brandMark.svg?raw";

/** Snapshot the real summary synchronously; font/image preparation may be async. */
export async function renderSummaryPng(
  summary: HTMLElement,
  title: string,
  date: string,
  filename: string,
): Promise<File> {
  const clone = summary.cloneNode(true) as HTMLElement;
  clone.querySelector(".share-actions")?.remove();
  clone.querySelector("h2")?.remove();
  const host = document.createElement("div");
  host.className = "route-page share-render-host";
  const card = document.createElement("div");
  card.className = "share-card";
  card.dir = "rtl";
  const brand = document.createElement("div");
  brand.className = "share-brand";
  const logo = document.createElement("span");
  logo.innerHTML = brandMark;
  const brandText = document.createElement("span");
  brandText.textContent = "هواچ · خلاصهٔ مسیر";
  brand.append(logo, brandText);
  const heading = document.createElement("h1");
  heading.className = "share-route-title";
  heading.textContent = title;
  const day = document.createElement("p");
  day.className = "share-date";
  day.textContent = new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "full",
    timeZone: "Asia/Tehran",
  }).format(new Date(`${date}T12:00:00+03:30`));
  card.append(brand, heading, day, clone);
  host.append(card);
  document.body.append(host);
  try {
    await document.fonts.ready;
    const blobData = async (url: string) => {
      const response = await fetch(url);
      if (!response.ok) throw new Error("دارایی تصویر دریافت نشد.");
      const blob = await response.blob();
      return await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      });
    };
    const theme =
      document.documentElement.dataset.theme === "light" ? "light" : "dark";
    const [background, regular, bold] = await Promise.all([
      blobData(`/new-design/backgrounds/route-desktop-${theme}.webp`),
      blobData("/new-design/fonts/Vazirmatn-Regular.woff2"),
      blobData("/new-design/fonts/Vazirmatn-Bold.woff2"),
    ]);
    const cardBackground = `linear-gradient(${theme === "dark" ? "rgba(8,41,56,.82),rgba(8,41,56,.97)" : "rgba(231,239,241,.72),rgba(231,239,241,.98)"}),url("${background}")`;
    card.style.backgroundImage = cardBackground;
    const width = 480,
      height = Math.ceil(card.getBoundingClientRect().height);
    // Resolve CSS variables and inherited colors while still in the document.
    const inline = (node: Element) => {
      const computed = getComputedStyle(node);
      let value = "";
      for (const property of computed) {
        if (property.startsWith("--") || property === "background-image")
          continue;
        value += `${property}:${computed.getPropertyValue(property)};`;
      }
      node.setAttribute(
        "style",
        value + (node === card ? `background-image:${cardBackground};` : ""),
      );
      for (const child of node.children) inline(child);
    };
    inline(card);
    const fonts = `<style>@font-face{font-family:Vazirmatn;src:url(${regular});font-weight:400}@font-face{font-family:Vazirmatn;src:url(${bold});font-weight:700}</style>`;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><foreignObject width="100%" height="100%"><div xmlns="http://www.w3.org/1999/xhtml">${fonts}${new XMLSerializer().serializeToString(card)}</div></foreignObject></svg>`;
    const image = new Image();
    image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
    await image.decode();
    const canvas = document.createElement("canvas");
    canvas.width = width * 2;
    canvas.height = height * 2;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("ساخت تصویر در این مرورگر ممکن نیست.");
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const png = await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob(
        (blob) =>
          blob ? resolve(blob) : reject(new Error("ساخت تصویر ناموفق بود.")),
        "image/png",
      ),
    );
    return new File([png], filename, { type: "image/png" });
  } finally {
    host.remove();
  }
}

/** HTTP IP previews have no secure clipboard; preserve focus and scrolling. */
export async function copyShareLink(url: string): Promise<boolean> {
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(url);
      return true;
    }
  } catch {
    /* Try the legacy user-gesture copy below. */
  }
  const previous = document.activeElement as HTMLElement | null;
  const input = document.createElement("textarea");
  input.value = url;
  input.style.cssText = "position:fixed;top:0;left:-10000px";
  document.body.append(input);
  input.select();
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } catch {
    /* Manual link selection remains available. */
  } finally {
    input.remove();
    previous?.focus({ preventScroll: true });
  }
  return copied;
}

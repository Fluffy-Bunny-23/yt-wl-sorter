(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const seen = new Set();
  let stablePasses = 0;
  let lastCount = 0;

  console.log("Scrolling Watch Later and collecting video IDs...");

  while (stablePasses < 4) {
    document.querySelectorAll('a[href*="watch?v="]').forEach((anchor) => {
      try {
        const url = new URL(anchor.href, location.origin);
        const id = url.searchParams.get("v");
        if (id) {
          seen.add(id);
        }
      } catch (error) {
        console.warn("Skipping malformed URL", anchor.href, error);
      }
    });

    window.scrollTo(0, document.documentElement.scrollHeight);
    await sleep(1500);

    if (seen.size === lastCount) {
      stablePasses += 1;
    } else {
      stablePasses = 0;
      lastCount = seen.size;
    }
  }

  const ids = [...seen];
  const text = ids.join("\n");

  console.log(`Collected ${ids.length} video IDs.`);
  console.log("Copy the block below into watch_later_ids.txt:");
  console.log("----- BEGIN WATCH LATER IDS -----");
  console.log(text);
  console.log("----- END WATCH LATER IDS -----");
})();

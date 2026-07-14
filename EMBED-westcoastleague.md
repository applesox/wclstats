# Embedding the WCL Standings page on westcoastleague.com

The standings page lives on GitHub Pages (`https://applesox.github.io/wclstats/`),
a different domain than westcoastleague.com, so it embeds as an **iframe**. Because
a cross-origin iframe can't size itself, the wclstats page now reports its height to
the host, and the snippet below listens for that and resizes the iframe, so there's
no inner scrollbar and it grows/shrinks as you switch tabs and filters.

The `?embed=1` on the URL hides the wclstats page's own title/subtitle so it doesn't
double up with the WordPress page heading.

## Prerequisite (do this first)
The embed-awareness (`?embed=1` + height reporting) ships with the wclstats page, so
publish it once before pasting the snippet:

```
powershell -ExecutionPolicy Bypass -File C:\ClaudeRoot\AppleSoxWCL\wclstats\refresh.ps1
```

## Paste-in snippet (WordPress "Custom HTML" block)

```html
<!-- WCL 2026 Standings — embedded from applesox.github.io/wclstats -->
<div class="wcl-standings-embed">
  <iframe id="wclStandings"
          src="https://applesox.github.io/wclstats/?embed=1"
          title="West Coast League 2026 Standings"
          loading="lazy"
          scrolling="no"
          style="width:100%;border:0;display:block;min-height:640px"
          height="900"></iframe>
</div>
<script>
(function(){
  var f = document.getElementById('wclStandings');
  window.addEventListener('message', function(e){
    if (e.origin !== 'https://applesox.github.io') return;   // only trust the wclstats origin
    var h = e.data && e.data.wclstatsHeight;
    if (h && f) f.style.height = h + 'px';
  });
})();
</script>
```

## How to place it
1. In wp-admin, open (or create) the page where standings should show — e.g. a
   **Standings** page you can then point the STATS mega-menu at.
2. Add a **Custom HTML** block (not a Paragraph block).
3. Paste the snippet above.
4. Update / Publish. Log in as an admin so WordPress keeps the `<script>` intact.

## If it doesn't auto-resize
Some security/caching plugins or page builders strip inline `<script>` from Custom
HTML. If the iframe stays a fixed height:
- Simplest fallback: delete the `<script>...</script>` block, keep the iframe, and
  set a taller fixed `height` (e.g. `height="1200"`), or change `scrolling="no"` to
  `scrolling="yes"` so the inner content scrolls.
- Or paste the whole snippet via a code-snippet plugin that allows scripts.

## Notes
- Test on the Local site first (`localhost:10017`) if you want to preview before prod.
- Prod is the manual WinSCP/DreamHost deploy for theme files, but this embed is just
  page content in wp-admin, so it publishes the moment you hit Update — no file deploy.
- The iframe always shows the current standings because it loads the live wclstats
  page, which refreshes nightly.

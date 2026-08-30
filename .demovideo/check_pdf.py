from playwright.sync_api import sync_playwright
import sys, os
with sync_playwright() as p:
    b=p.chromium.launch(args=['--no-sandbox','--disable-dev-shm-usage','--force-color-profile=srgb'])
    pg=b.new_page(viewport={'width':900,'height':1300}, device_scale_factor=1.4)
    pg.goto('file:///app/.demovideo/pdf/index.html', wait_until='load')
    pg.wait_for_timeout(3200)
    res = pg.evaluate('''() => {
      const out=[];
      document.querySelectorAll('.page').forEach((pageEl,i)=>{
        const inner = pageEl.querySelector(':scope > div:nth-child(3)') || pageEl;
        const pr = pageEl.getBoundingClientRect();
        const footEl = pageEl.querySelector('.foot');
        const footTop = footEl ? footEl.getBoundingClientRect().top - pr.top : pr.height;
        let maxBottom = 0;
        inner.querySelectorAll('*').forEach(el=>{
          const r = el.getBoundingClientRect();
          if (r.height>0) maxBottom = Math.max(maxBottom, r.bottom - pr.top);
        });
        out.push({page:i+1, over: Math.round(maxBottom-footTop)});
      });
      return out;
    }''')
    bad=[r for r in res if r['over'] > -6]
    for r in res:
        print(f"p{r['page']:02d} slack={-r['over']:5d}{'   <-- OVERFLOW' if r['over']>-6 else ''}")
    if len(sys.argv)>1 and sys.argv[1]=='shots':
        os.makedirs('chk/pdfpg', exist_ok=True)
        for i,el in enumerate(pg.query_selector_all('.page')):
            el.screenshot(path=f'chk/pdfpg/p{i+1:02d}.png')
    b.close()
print('OVERFLOWS:', len(bad))

from playwright.sync_api import sync_playwright
import sys
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1100,'height':1960},device_scale_factor=2)
    pg.goto('file://'+sys.argv[1]); pg.wait_for_timeout(800)
    ov=pg.evaluate("(()=>{const p=document.getElementById('p');const c=p.querySelector('.cols');return [p.scrollHeight,c.scrollHeight,c.clientHeight,document.querySelector('.ed').getBoundingClientRect().bottom,document.querySelector('.inside').getBoundingClientRect().top]})()")
    print(ov)
    pg.locator('#p').screenshot(path=sys.argv[2]); b.close()

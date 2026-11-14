#!/usr/bin/env python3
"""Optional UI smoke test: needs Playwright + Chromium, not a Skill runtime dependency."""
from pathlib import Path
import argparse
from playwright.sync_api import sync_playwright

def main():
    ap=argparse.ArgumentParser();ap.add_argument("html");ap.add_argument("--screenshot");a=ap.parse_args()
    path=Path(a.html).resolve()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={"width":1440,"height":930},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        # This sandbox blocks file:// navigation administratively; DOM is loaded
        # with set_content to exercise the exact generated HTML and JS.
        page.set_content(path.read_text(encoding='utf-8'),wait_until='load')
        assert 'SYNTHETIC FIXTURE' in page.locator('#heroTitle').inner_text()
        assert page.locator('#stats .stat').count()==5
        page.locator('[data-view="items"]').click()
        assert page.locator('#itemsRows tr').count()==11
        page.locator('#search').fill('动态特征融合')
        assert page.locator('#itemsRows tr').count()==1
        page.locator('#search').fill('')
        page.locator('#filterLifecycle').select_option('parked')
        assert page.locator('#itemsRows tr').count()==1
        page.locator('#itemsRows [data-open="IDEA-0001"]').click()
        assert page.locator('#drawer').evaluate('(el)=>el.classList.contains("open")')
        assert '仅 synthetic toy data' in page.locator('#drawerContent').inner_text()
        page.locator('#drawerClose').click()
        page.locator('[data-view="archive"]').click()
        assert page.locator('#archiveCards .archive-card').count()==2
        page.locator('#archiveSearch').fill('复杂对抗')
        assert page.locator('#archiveCards .archive-card').count()==1
        page.locator('[data-view="graph"]').click()
        assert page.locator('#relationSvg g').count()==11
        page.locator('[data-view="history"]').click()
        assert page.locator('#events .event').count()>10
        page.locator('#role').select_option('mentor')
        page.locator('[data-view="overview"]').click()
        assert '导师审批' in page.locator('#priorityTitle').inner_text()
        assert not errors, 'JS runtime errors: '+repr(errors)
        if a.screenshot:page.screenshot(path=str(Path(a.screenshot).resolve()),full_page=True)
        print('PASS: generated HTML loaded in Chromium via set_content; 5 counters, search, lifecycle filter, drawer, archive, SVG, history, mentor view; no JS errors')
        browser.close()
if __name__=='__main__':main()

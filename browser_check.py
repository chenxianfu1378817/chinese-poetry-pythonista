"""Optional browser regression: pip install playwright; playwright install chromium.
Uses a real local server; only iOS UI, keychain and device voices are simulated.
"""
import json, shutil, sys, tempfile, time
from pathlib import Path
from unittest.mock import patch
from playwright.sync_api import sync_playwright
from poetry_app.app import run
from poetry_app.core import Library
from test_support import fake_ui

ROOT=Path(__file__).resolve().parent

def check_theme_switching(page):
    nav=page.locator('#nav')
    nav.get_by_role('button',name='设置',exact=True).click()
    for mode,label in [('dark','深色'),('light','浅色')]:
        page.get_by_role('button',name=label,exact=True).click()
        backgrounds=set();accents=set()
        for theme in page.evaluate('Object.keys(themes)'):
            page.get_by_role('button',name=theme,exact=True).click()
            page.wait_for_function('bridgeQueue.length===0')
            colors=page.evaluate('''()=>{let s=getComputedStyle(document.documentElement);return {theme:user.theme,scheme:s.colorScheme,bg:s.getPropertyValue('--bg'),accent:s.getPropertyValue('--accent')}}''')
            assert colors['theme']==theme and colors['scheme']==mode
            assert page.locator('.themes .active').inner_text()==theme
            backgrounds.add(colors['bg']);accents.add(colors['accent'])
        assert len(backgrounds)==8 and len(accents)==8
    page.get_by_role('button',name='跟随系统',exact=True).click()
    page.emulate_media(color_scheme='dark')
    page.wait_for_function("document.documentElement.style.colorScheme==='dark'")
    page.emulate_media(color_scheme='light')
    page.wait_for_function("document.documentElement.style.colorScheme==='light'")
    page.get_by_role('button',name='深色',exact=True).click()
    page.wait_for_function('bridgeQueue.length===0');page.reload()
    page.wait_for_function("user.theme==='赤陶棕' && user.mode==='dark'")
    assert page.evaluate('document.documentElement.style.colorScheme')=='dark'
    nav.get_by_role('button',name='设置',exact=True).click()
    assert page.locator('.themes .active').inner_text()=='赤陶棕'
    page.get_by_role('button',name='活力橙',exact=True).click()
    page.get_by_role('button',name='跟随系统',exact=True).click()
    page.wait_for_function('bridgeQueue.length===0')
    nav.get_by_role('button',name='今日',exact=True).click()

def check():
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(ROOT/'data',Path(tmp)/'data')
        lib=Library(tmp)
        legacy=json.loads((ROOT/'data/poems.json').read_text())
        old=next(p for p in legacy if p['id'] not in lib.index)
        lib.favorite(old['id']);lib.settings({'id':old['id'],'note':'旧版手记保留'})
        ui=fake_ui()
        with patch.dict(sys.modules,{'ui':ui}):reader=run(tmp)
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch()
                page=browser.new_page(viewport={'width':390,'height':844})
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.add_init_script('''window.voiceTest={voices:[],spoken:[]};let voiceChange;
                window.testLoadVoices=()=>{voiceTest.voices=[{voiceURI:'zh-basic',name:'中文普通',lang:'zh-CN',localService:true},{voiceURI:'zh-better',name:'中文优化音质',lang:'zh-CN',localService:true},{voiceURI:'remote',name:'Remote',lang:'zh-CN',localService:false}];voiceChange()};
                Object.defineProperty(window,'speechSynthesis',{value:{getVoices:()=>voiceTest.voices,addEventListener:(e,fn)=>{voiceChange=fn},speak:u=>{voiceTest.spoken.push(u);u.onstart()},cancel:()=>{}}});
                window.SpeechSynthesisUtterance=class{constructor(t){this.text=t}};''')
                page.goto(reader.base)
                page.wait_for_function('boot.stats.total===25324 && poems.length<100')
                check_theme_switching(page)
                assert '赏析' not in page.locator('body').inner_text()
                nav=page.locator('#nav')
                nav.get_by_role('button',name='诗库',exact=True).click()
                page.wait_for_function('catalogRows.length===40')
                page.get_by_role('combobox',name='作者筛选').select_option('李白')
                page.wait_for_function('catalogRows.length===40 && document.querySelector("#results .counter").textContent.includes("1173")')
                page.get_by_role('button',name='再看40首',exact=True).click()
                page.wait_for_function('catalogRows.length===80')
                assert page.evaluate('new Set(catalogRows).size===80')
                page.get_by_role('button',name='切换简繁',exact=True).click()
                page.wait_for_function('bridgeQueue.length===0 && catalogRows.length===40')
                assert page.get_by_role('combobox',name='作者筛选').input_value()=='李白'
                page.get_by_role('combobox',name='作者筛选').select_option('')
                search=page.get_by_placeholder('搜索标题、作者、诗句（简繁皆可）')
                for query in ['王维','王維','空山新雨后','大江東去','寻寻觅觅','长恨歌']:
                    search.fill(query)
                    page.wait_for_function('(q)=>query===q && !document.querySelector("#results").textContent.includes("正在查询") && catalogRows.length>0',arg=query)
                    page.wait_for_timeout(250)
                    assert page.locator('.poem').count()>0,query
                # A pending search must not write into another tab.
                search.fill('白居易');nav.get_by_role('button',name='设置',exact=True).click()
                page.wait_for_timeout(250)
                page.locator('#aiKey').fill('PRIVATE_DRAFT_NOT_REAL')
                page.evaluate('testLoadVoices()')
                assert page.locator('#deviceVoice option').count()==3
                assert page.locator('#aiKey').input_value()=='PRIVATE_DRAFT_NOT_REAL'
                page.get_by_role('combobox',name='本机中文声音').select_option(label='中文优化音质 · zh-CN')
                page.get_by_role('slider',name='朗读语速').fill('0.8')
                page.get_by_role('slider',name='朗读语速').dispatch_event('change')
                page.get_by_role('button',name='试听所选声音',exact=True).click()
                assert page.evaluate('voiceTest.spoken[0].voice.voiceURI')=='zh-better'
                assert page.evaluate('voiceTest.spoken[0].rate')==0.8
                page.get_by_role('button',name='简体',exact=True).click()
                assert page.locator('#aiKey').input_value()=='PRIVATE_DRAFT_NOT_REAL'
                page.wait_for_function('bridgeQueue.length===0')
                # Legacy IDs and notes are available after expansion.
                nav.get_by_role('button',name='收藏',exact=True).click()
                page.wait_for_function('catalogRows.length===1')
                page.locator('.poem').click()
                assert page.locator('#note').input_value()=='旧版手记保留'
                # Freshly paged poems support notes, favorites and learning.
                nav.get_by_role('button',name='诗库',exact=True).click()
                search=page.get_by_placeholder('搜索标题、作者、诗句（简繁皆可）')
                search.fill('空山新雨后')
                page.wait_for_function('catalogRows.length>0 && query==="空山新雨后" && !document.querySelector("#results").textContent.includes("正在查询")')
                page.wait_for_timeout(250);page.locator('.poem').first.click()
                ident=page.evaluate('selected.id')
                assert '空山新雨后' in page.locator('.verse').inner_text()
                page.locator('#note').fill('王維：這是我的手記')
                page.get_by_role('button',name='保存手记',exact=True).click()
                page.get_by_role('button',name='♡ 收藏',exact=True).click()
                page.get_by_role('slider',name='阅读字号').fill('31')
                page.get_by_role('slider',name='阅读字号').dispatch_event('change')
                page.get_by_role('button',name='背诵',exact=True).click()
                page.get_by_role('button',name='标记已背熟',exact=True).click()
                page.wait_for_function('bridgeQueue.length===0')
                page.reload();page.wait_for_function('boot.stats.total===25324')
                page.evaluate('openPoem('+json.dumps(ident)+')')
                assert page.locator('#note').input_value()=='王維：這是我的手記'
                assert page.get_by_role('button',name='♥ 已收藏',exact=True).count()==1
                assert page.evaluate('user.font_size')==31
                assert page.evaluate('user.learning['+json.dumps(ident)+'].status')=='mastered'
                page.get_by_role('button',name='切换简繁',exact=True).click()
                assert '新雨後' in page.locator('.verse').inner_text()
                assert page.locator('#note').input_value()=='王維：這是我的手記'
                nav.get_by_role('button',name='设置',exact=True).click()
                page.get_by_role('button',name='原文',exact=True).click()
                page.wait_for_function('bridgeQueue.length===0')
                nav.get_by_role('button',name='今日',exact=True).click()
                for _ in range(5):
                    page.get_by_role('button',name='↻ 随机遇见',exact=True).click()
                    page.wait_for_selector('.verse')
                    assert page.evaluate('selected.id in Object.fromEntries(originals.map(p=>[p.id,1]))')
                    nav.get_by_role('button',name='今日',exact=True).click()
                for width,height in [(320,568),(390,844),(844,390),(1024,768)]:
                    page.set_viewport_size({'width':width,'height':height})
                    nav.get_by_role('button',name='诗库',exact=True).click()
                    page.wait_for_function('catalogRows.length===40')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    assert nav.bounding_box()['y']+nav.bounding_box()['height']<=height+1
                page.wait_for_function('bridgeQueue.length===0')
                page.get_by_role('button',name='退出阅读',exact=True).click()
                for _ in range(20):
                    if reader.was_closed:break
                    time.sleep(.05)
                assert reader.was_closed
                assert not errors,errors
                browser.close()
        finally:reader.close();ui.shutdown()
    print('PASS: eight distinct light/dark themes, system appearance and persistence; 25,324-record local catalog; author filter; pagination; cross-script search; saved legacy IDs; notes, favorites, learning and font persistence; local voice selection; four layouts; exit. No real iPhone or paid AI test.')

if __name__=='__main__':check()

"""Real Chromium MV3 integration; explicit separate CI job, never a mocked browser."""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest

from observador.web_events import validate_web_export


@unittest.skipUnless(os.environ.get('OBS_BROWSER_TEST') == '1','Real browser test enabled in dedicated web CI job')
class BrowserExtensionTest(unittest.TestCase):
    def test_offline_bridge_ack_survives_real_service_worker_stop_and_restart(self):
        from playwright.sync_api import sync_playwright,expect
        from observador.offline_bridge import OfflineBridge,read_batch,canonical
        root=Path(__file__).resolve().parents[1]
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',8765),functools.partial(QuietHandler,directory=str(root/'tests/fixtures/web')))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as profile,sync_playwright() as p:
                extension=str(root/'browser-extension')
                context=p.chromium.launch_persistent_context(profile,executable_path=os.environ.get('OBS_CHROMIUM_PATH') or p.chromium.executable_path,
                    headless=True,ignore_default_args=['--disable-extensions'],args=['--no-sandbox',f'--disable-extensions-except={extension}',
                    f'--load-extension={extension}','--disable-background-networking','--disable-sync','--no-first-run'])
                bridge=OfflineBridge(Path(profile)/'inbox/bridge.sqlite3')
                try:
                    worker=context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker')
                    extension_id=worker.url.split('/')[2]
                    page=context.new_page();page.goto('http://127.0.0.1:8765/synthetic-lab/index.html')
                    page.wait_for_selector('#observador-lab-status')
                    tab_id=worker.evaluate('async()=> (await chrome.tabs.query({url:"http://127.0.0.1/*"}))[0].id')
                    popup=context.new_page();popup.goto(f'chrome-extension://{extension_id}/popup.html')
                    popup.evaluate('(id)=>chrome.tabs.update(id,{active:true})',tab_id);popup.reload()
                    popup.wait_for_function('typeof tabId === "number"')
                    popup.evaluate("document.getElementById('start').click()")
                    page.wait_for_function("document.getElementById('observador-lab-status').textContent.includes('ATIVO')")
                    declared=worker.evaluate('async(id)=>{const s=(await chrome.storage.session.get("sessions")).sessions[id];return {kind:"web",version:1,instance:s.id,origin:"http://127.0.0.1:8765",tab_slot:s.slot};}',tab_id)
                    bridge.authorize(declared);bridge.control('start')
                    ticket=Path(profile)/'ticket.json';ticket.write_text(json.dumps(bridge.ticket(declared['instance'])))
                    popup.locator('#bridge-ticket').set_input_files(ticket)
                    expect(popup.locator('#bridge-status')).to_have_text('Ticket aceito')
                    page.locator('#save').click();page.wait_for_timeout(300)
                    def download_batch():
                        with popup.expect_download() as downloaded:
                            popup.evaluate("document.getElementById('bridge-export').click()")
                        return read_batch(downloaded.value.path())
                    batch=download_batch()
                    self.assertTrue(batch['events'])
                    ack=bridge.ingest(batch)
                    self.assertEqual(bridge.ingest(batch),ack)
                    # ACTUAL target termination in this disposable browser profile.
                    cdp=context.browser.new_browser_cdp_session()
                    restarted=[];destroyed=[]
                    context.on('serviceworker',lambda value:restarted.append(value))
                    targets=cdp.send('Target.getTargets')['targetInfos']
                    matches=[target for target in targets if target['type']=='service_worker' and target['url']==worker.url]
                    self.assertEqual(len(matches),1,'Owned extension worker target is ambiguous')
                    target_id=matches[0]['targetId']
                    cdp.on('Target.targetDestroyed',lambda data:destroyed.append(True) if data['targetId']==target_id else None)
                    cdp.send('Target.setDiscoverTargets',{'discover':True})
                    origin=worker.evaluate('performance.timeOrigin')
                    result=cdp.send('Target.closeTarget',{'targetId':target_id})
                    self.assertTrue(result['success'],'Owned worker target could not be closed')
                    deadline=time.monotonic()+10
                    while (not restarted or not destroyed) and time.monotonic()<deadline:page.wait_for_timeout(100)
                    self.assertTrue(destroyed,'No actual worker target destruction observed')
                    self.assertTrue(restarted,'Worker did not actually restart')
                    replacement=[w for w in restarted if w.url==worker.url][-1]
                    self.assertNotEqual(replacement.evaluate('performance.timeOrigin'),origin)
                    page.wait_for_function("document.getElementById('observador-lab-status').textContent.includes('ENCERRADO')")
                    retry=download_batch()
                    self.assertEqual(canonical(retry),canonical(batch))
                    self.assertEqual(bridge.ingest(retry),ack)
                    acknowledgment=Path(profile)/'ack.json';acknowledgment.write_text(json.dumps(ack))
                    popup.locator('#bridge-ack').set_input_files(acknowledgment)
                    expect(popup.locator('#bridge-status')).to_have_text('ACK confirmado')
                    pending=replacement.evaluate('async(id)=>(await chrome.storage.session.get("sessions")).sessions[id].bridge.pending',tab_id)
                    self.assertIsNone(pending)
                    self.assertEqual(len(bridge.source_events()[0]['events']),len(batch['events']))
                    print('SYNTHETIC_BRIDGE_RESTART_VERIFIED',json.dumps(dict(events=len(batch['events']),worker_restarted=True,
                          receipt_replayed=True,producer_stopped=True,human_acceptance=False)))
                finally:bridge.close();context.close()
        finally:server.shutdown();server.server_close();thread.join(timeout=3)

    def test_real_mv3_allowlist_privacy_pause_navigation_limits_and_expiry(self):
        from playwright.sync_api import sync_playwright
        root=Path(__file__).resolve().parents[1]
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',8765),functools.partial(QuietHandler,directory=str(root/'tests/fixtures/web')))
        server.daemon_threads=True
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as profile,sync_playwright() as p:
                extension=str(root/'browser-extension')
                context=p.chromium.launch_persistent_context(profile,executable_path=os.environ.get('OBS_CHROMIUM_PATH') or p.chromium.executable_path,
                    headless=True,ignore_default_args=['--disable-extensions'],args=['--no-sandbox',f'--disable-extensions-except={extension}',f'--load-extension={extension}',
                                        '--disable-background-networking','--disable-sync','--no-first-run'])
                try:
                    worker=context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker')
                    extension_id=worker.url.split('/')[2]
                    page=context.new_page()
                    page.goto('http://127.0.0.1:8765/synthetic-lab/index.html')
                    page.wait_for_selector('#observador-lab-status')
                    self.assertIn('DESATIVADO',page.locator('#observador-lab-status').inner_text())
                    page.locator('#save').click()
                    self.assertEqual(worker.evaluate('async()=> (await chrome.storage.session.get("sessions")).sessions || {}'),{})
                    tab_id=worker.evaluate('async()=> (await chrome.tabs.query({url:"http://127.0.0.1/*"}))[0].id')
                    popup=context.new_page()
                    popup.goto(f'chrome-extension://{extension_id}/popup.html')
                    # Keep the synthetic tab selected, then execute actual popup JS.
                    popup.evaluate('(id)=>chrome.tabs.update(id,{active:true})',tab_id)
                    popup.reload()
                    popup.wait_for_function('typeof tabId === "number"')
                    popup.evaluate("document.getElementById('start').click()")
                    page.wait_for_function("document.getElementById('observador-lab-status').textContent.includes('ATIVO')")
                    for selector in ('#save','#menu','#menuitem','#tab','#register','#submit'):
                        page.locator(selector).click()
                    page.locator('#normal').fill('CLIENTE-FICTICIO-NUNCA-EXPORTAR')
                    page.locator('#password').fill('SENHA-FICTICIA-NUNCA-EXPORTAR')
                    page.locator('#password').click()
                    page.wait_for_timeout(400)
                    def report():return popup.evaluate('async()=> (await chrome.runtime.sendMessage({kind:"export",tabId})).report')
                    before=report()
                    self.assertTrue({'save','open_menu','select_menu','select_tab','register','submit'} <= {e['action'] for e in before['events']})
                    popup.evaluate("document.getElementById('pause').click()")
                    page.wait_for_function("document.getElementById('observador-lab-status').textContent.includes('PAUSADO')")
                    count=len(report()['events'])
                    page.locator('#save').click()
                    self.assertEqual(len(report()['events']),count)
                    popup.evaluate("document.getElementById('resume').click()")
                    page.wait_for_function("document.getElementById('observador-lab-status').textContent.includes('ATIVO')")
                    page.locator('#next').click()
                    page.wait_for_selector('#review')
                    page.wait_for_function("document.getElementById('observador-lab-status').textContent.includes('ATIVO')")
                    page.locator('#review').click()
                    button=page.locator('#review').bounding_box()
                    for _ in range(60):page.mouse.click(button['x']+5,button['y']+5)
                    exported=report()
                    validate_web_export(exported)
                    raw=json.dumps(exported)
                    for secret in ('CLIENTE-FICTICIO','SENHA-FICTICIA','NAO_EXPORTAR','SIGILO-FICTICIO','127.0.0.1','http:'):
                        self.assertNotIn(secret,raw)
                    self.assertIn('review',{e['action'] for e in exported['events']})
                    self.assertGreaterEqual(sum(e['action']=='transition' for e in exported['events']),2)
                    self.assertGreater(exported['dropped'],0)
                    self.assertLessEqual(len(exported['events']),256)
                    with popup.expect_download() as downloading:
                        popup.evaluate("document.getElementById('export').click()")
                    download=downloading.value
                    validate_web_export(json.loads(Path(download.path()).read_text()))
                    # Inject an expired deadline; the actual 15-minute human trial is separate.
                    worker.evaluate('async(id)=>{const d=await chrome.storage.session.get("sessions");d.sessions[id].expires=Date.now()-1;await chrome.storage.session.set(d);}',tab_id)
                    page.wait_for_function("document.getElementById('observador-lab-status').textContent.includes('ENCERRADO')")
                    final=report()
                    page.locator('#review').click()
                    self.assertEqual(len(report()['events']),len(final['events']))
                    popup.evaluate("document.getElementById('start').click()")
                    page.wait_for_function("document.getElementById('observador-lab-status').textContent.includes('ATIVO')")
                    # A new worker time origin fails closed; injected state is not a real worker restart trial.
                    worker.evaluate('async(id)=>{const d=await chrome.storage.session.get("sessions");d.sessions[id].workerOrigin=-1;await chrome.storage.session.set(d);}',tab_id)
                    page.wait_for_function("document.getElementById('observador-lab-status').textContent.includes('ENCERRADO')")
                    # A different port and a different path cannot start or export a session.
                    self.assertFalse(worker.evaluate('()=>allowed("http://127.0.0.1:8766/synthetic-lab/index.html")'))
                    self.assertFalse(worker.evaluate('()=>allowed("https://example.com/synthetic-lab/index.html")'))
                    page.goto('http://127.0.0.1:8765/outside/')
                    self.assertEqual(page.locator('#observador-lab-status').count(),0)
                    print('SYNTHETIC_MV3_VERIFIED',json.dumps({'events':len(final['events']),'browser':context.browser.version,'human_acceptance':False}))
                finally:context.close()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)

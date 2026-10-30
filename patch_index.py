#!/usr/bin/env python3
"""Kurir-Q index.html Patcher — dijalankan oleh GitHub Actions"""
import os, re, sys

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

EMOJI  = os.environ.get('APP_EMOJI', '🛵')
BG     = os.environ.get('ICON_BG', '#2563eb')
NAME   = os.environ.get('APP_NAME', 'Kurir-Q')
BG_URL = BG.replace('#', '%23')
changes = []

def replace_function(name, new_code):
    global html
    start = -1
    for prefix in [f'function {name}(', f'async function {name}(']:
        idx = html.find(prefix)
        if idx != -1:
            start = idx
            break
    if start == -1:
        return False
    brace = html.find('{', start)
    if brace == -1:
        return False
    depth, i = 0, brace
    while i < len(html):
        if html[i] == '{':
            depth += 1
        elif html[i] == '}':
            depth -= 1
            if depth == 0:
                break
        i += 1
    if depth != 0:
        return False
    html = html[:start] + new_code + html[i+1:]
    return True

# ---- PATCH 1: Normalisasi WA ----
NEW_WA = r'''function normalizeWhatsApp(input){
    if(!input)return '';
    let digits=String(input).replace(/\D/g,'');
    if(!digits)return '';
    if(digits.startsWith('0062'))digits=digits.substring(2);
    while(digits.startsWith('00'))digits=digits.substring(2);
    while(digits.startsWith('6262'))digits='62'+digits.substring(4);
    while(digits.startsWith('620'))digits='62'+digits.substring(3);
    if(digits.startsWith('0'))digits='62'+digits.substring(1);
    else if(digits.startsWith('8'))digits='62'+digits;
    else if(!digits.startsWith('62'))digits='62'+digits;
    return digits;
}
function validateWAFormat(wa){
    if(!wa||!String(wa).trim())return{type:'empty',valid:false,reason:'Nomor kosong'};
    const digits=String(wa).replace(/\D/g,'');
    if(/^628[1-9]\d{6,12}$/.test(digits))return{type:'mobile',valid:true,reason:'Mobile OK'};
    if(/^62[2-9]\d{6,11}$/.test(digits))return{type:'landline',valid:false,reason:'Telepon rumah'};
    if(digits.length<10)return{type:'invalid',valid:false,reason:'Terlalu pendek'};
    if(digits.length>15)return{type:'invalid',valid:false,reason:'Terlalu panjang'};
    if(digits.startsWith('62'))return{type:'unknown',valid:true,reason:'Format aneh'};
    return{type:'invalid',valid:false,reason:'Format aneh'};
}
function importNormalizeWA(rawInput){
    if(!rawInput||!String(rawInput).trim())return{wa:'',warning:null};
    const normalized=normalizeWhatsApp(rawInput);
    const check=validateWAFormat(normalized);
    if(check.type==='mobile')return{wa:normalized,warning:null};
    if(check.type==='landline')return{wa:normalized,warning:`Landline: "${rawInput}"`,type:'landline'};
    return{wa:normalized,warning:`Aneh: "${rawInput}" -> "${normalized}"`,type:'unknown'};
}'''
if replace_function('normalizeWhatsApp', NEW_WA):
    changes.append('WA normalize + validate + import')

# ---- PATCH 2: analyzeWhatsAppNumbers ----
NEW_ANALYZE = r'''function analyzeWhatsAppNumbers(addresses){
    const issues={valid:[],double62:[],leading62_0:[],fixedLine:[],tooShort:[],tooLong:[],unknown:[],empty:[]};
    (addresses||[]).forEach(a=>{
        const raw=(a.whatsapp||'').trim();
        const name=a.recipient_name||'(tanpa nama)';
        if(!raw){issues.empty.push({name,raw});return;}
        const rawDigits=raw.replace(/\D/g,'');
        const normalized=normalizeWhatsApp(raw);
        const check=validateWAFormat(normalized);
        if(/^6262/.test(rawDigits)){issues.double62.push({name,raw,fixed:normalized});return;}
        if(/^620/.test(rawDigits)){issues.leading62_0.push({name,raw,fixed:normalized});return;}
        switch(check.type){
            case 'mobile':issues.valid.push({name,raw,fixed:normalized});break;
            case 'landline':issues.fixedLine.push({name,raw,fixed:normalized,reason:check.reason});break;
            case 'invalid':
                if(check.reason.indexOf('pendek')>=0)issues.tooShort.push({name,raw,fixed:normalized});
                else if(check.reason.indexOf('panjang')>=0)issues.tooLong.push({name,raw,fixed:normalized});
                else issues.unknown.push({name,raw,fixed:normalized});
                break;
            default:issues.unknown.push({name,raw,fixed:normalized});
        }
    });
    return issues;
}'''
if replace_function('analyzeWhatsAppNumbers', NEW_ANALYZE):
    changes.append('WA analyze')

# ---- PATCH 3: processCSVImport call ----
old = "whatsapp:waRaw?normalizeWhatsApp(waRaw):''"
new = "whatsapp:(function(){const r=importNormalizeWA(waRaw);return r.wa;})()"
if old in html:
    html = html.replace(old, new)
    changes.append('CSV import call')

# ---- PATCH 4: warnings lengkap ----
old_warn = "if(issues.fixedLine.length>0)warnings.push(`📞 ${issues.fixedLine.length} nomor telpon rumah`);"
new_warn = '''if(issues.valid.length>0)warnings.push(`✅ ${issues.valid.length} mobile valid`);
    if(issues.double62.length>0)warnings.push(`🔁 ${issues.double62.length} nomor "62-62" dobel`);
    if(issues.leading62_0.length>0)warnings.push(`⚠️ ${issues.leading62_0.length} nomor "62-0..."`);
    if(issues.fixedLine.length>0)warnings.push(`📞 ${issues.fixedLine.length} TELEPON RUMAH (tidak bisa WA)`);
    if(issues.tooShort.length>0)warnings.push(`📏 ${issues.tooShort.length} terlalu pendek`);
    if(issues.tooLong.length>0)warnings.push(`📏 ${issues.tooLong.length} terlalu panjang`);
    if(issues.unknown.length>0)warnings.push(`❓ ${issues.unknown.length} format aneh`);
    if(issues.empty.length>0)warnings.push(`📭 ${issues.empty.length} kosong`);'''
if old_warn in html:
    html = html.replace(old_warn, new_warn)
    changes.append('warnings lengkap')

# ---- PATCH 5: emoji ----
old = 'animation:bootPulse 1.5s infinite">📦</div>'
new = f'animation:bootPulse 1.5s infinite">{EMOJI}</div>'
if old in html:
    html = html.replace(old, new)
    changes.append('boot emoji')

old = '<header><h1>📦 Kurir-Q</h1>'
new = f'<header><h1>{EMOJI} {NAME}</h1>'
if old in html:
    html = html.replace(old, new)
    changes.append('header emoji')

old = "dominant-baseline='middle'>📦</text>"
new = f"dominant-baseline='middle'>{EMOJI}</text>"
if old in html:
    html = html.replace(old, new)
    changes.append('apple icon emoji')

# ---- PATCH 6: warna (opsional) ----
if BG.lower() != '#2563eb':
    old = '#boot-splash{position:fixed;inset:0;background:#2563eb;'
    new = f'#boot-splash{{position:fixed;inset:0;background:{BG};'
    if old in html:
        html = html.replace(old, new)
        changes.append('boot BG')
    html, n = re.subn(r'<meta name="theme-color" content="#[0-9a-fA-F]{6}">',
                      f'<meta name="theme-color" content="{BG}">', html)
    if n:
        changes.append('theme-color')
    if "fill='%232563eb'" in html:
        html = html.replace("fill='%232563eb'", f"fill='{BG_URL}'")
        changes.append('apple BG')

# ---- SIMPAN ----
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n📊 Total patch: {len(changes)}")
for c in changes:
    print(f"  ✅ {c}")

if len(changes) < 3:
    print("\n⚠️ Hanya sedikit patch berhasil — cek struktur index.html")
    sys.exit(1)
else:
    print("\n✅ Patch selesai.")

# ============================================================
# PATCH 7: Fix export JSON/CSV untuk APK (Capacitor WebView)
# ============================================================

NEW_DOWNLOAD_HELPER = r'''async function downloadFile(filename, content, mimeType){
    mimeType = mimeType || 'application/octet-stream';
    
    if (navigator.share && navigator.canShare) {
        try {
            const file = new File([content], filename, { type: mimeType });
            if (navigator.canShare({ files: [file] })) {
                await navigator.share({ files: [file], title: filename });
                return { success: true, method: 'share' };
            }
        } catch(e) {
            if (e.name === 'AbortError') return { success: false, method: 'cancelled' };
        }
    }
    
    try {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        setTimeout(function(){ document.body.removeChild(a); URL.revokeObjectURL(url); }, 200);
        return { success: true, method: 'download' };
    } catch(e) {
        showManualCopyModal(filename, content);
        return { success: false, method: 'manual' };
    }
}
function showManualCopyModal(filename, content){
    const safe = String(content).replace(/</g, '&lt;').replace(/&/g, '&amp;');
    document.getElementById('modal-content').innerHTML = 
        '<h2>📋 Salin Manual</h2>' +
        '<p style="font-size:12px;color:var(--text-light);margin-bottom:8px">Download otomatis gagal di perangkat ini.<br>Tap tombol <strong>Salin</strong>, lalu paste ke aplikasi Notes/File Manager, simpan sebagai <strong>' + filename + '</strong></p>' +
        '<textarea id="manual-copy-text" readonly style="width:100%;height:280px;font-family:monospace;font-size:10px;padding:8px;border:1px solid var(--border);border-radius:4px;box-sizing:border-box;background:var(--bg-alt);color:var(--text)">' + safe + '</textarea>' +
        '<div style="display:flex;gap:8px;margin-top:12px">' +
        '<button class="btn-primary" style="flex:1;padding:10px" onclick="copyManualContent()">📋 Salin</button>' +
        '<button class="btn-secondary" style="flex:1;padding:10px" onclick="closeModal()">Tutup</button>' +
        '</div>';
    document.getElementById('modal').classList.add('active');
}
async function copyManualContent(){
    const ta = document.getElementById('manual-copy-text');
    if (!ta) return;
    try {
        await navigator.clipboard.writeText(ta.value);
        showModal('Sukses', '✓ Teks tersalin ke clipboard');
    } catch(e) {
        ta.select();
        document.execCommand('copy');
        showModal('Sukses', '✓ Teks tersalin');
    }
}'''

NEW_EXPORT_JSON = r'''async function exportJSON(){
    const addresses = await getAllAddresses();
    if (addresses.length === 0) { showModal('Info', '⚠️ Tidak ada data'); return; }
    const data = { version: '1.0', exported_at: new Date().toISOString(), addresses };
    const json = JSON.stringify(data, null, 2);
    const fname = 'kurir-q-backup-' + new Date().toISOString().split('T')[0] + '.json';
    const result = await downloadFile(fname, json, 'application/json');
    if (result.success) {
        if (result.method === 'share') {
            showModal('Sukses', '✓ Backup JSON (' + addresses.length + ' alamat)\n\nFile dibagikan via menu Share.\nPilih aplikasi untuk menyimpan.');
        } else {
            showModal('Sukses', '✓ Backup JSON: ' + addresses.length + ' alamat');
        }
    }
}'''

NEW_EXPORT_CSV = r'''async function exportCSV(){
    const addresses = await getAllAddresses();
    if (addresses.length === 0) { showModal('Info', '⚠️ Tidak ada data'); return; }
    const h = ['id','nama','no_wa','gang','nomor','rt','rw','kelurahan','alamat','latitude','longitude','patokan','status_pembayaran','masalah','tipe_lokasi','visit_count','kunjungan_terakhir','catatan','delivery_status','penerima_lain'];
    const rows = addresses.map(a => [a.id,a.recipient_name,a.whatsapp||'',a.gang,a.house_number,a.rt||'',a.rw||'',a.kelurahan||'',a.address,a.latitude,a.longitude,a.landmark,a.payment_status,(a.problem_tags||[]).join('; '),a.location_type,a.visit_count||1,formatDate(a.last_visit_at||a.created_at),a.description,a.delivery_status,(a.recipients||[]).filter(r=>r.name!==a.recipient_name).map(r=>r.name+':'+r.status).join('; ')]);
    let csv = h.join(',') + '\n';
    rows.forEach(r => { csv += r.map(c => (typeof c==='string'&&(c.includes(',')||c.includes('"')||c.includes('\n'))) ? '"'+c.replace(/"/g,'""')+'"' : (c||'')).join(',') + '\n'; });
    const fname = 'kurir-q-backup-' + new Date().toISOString().split('T')[0] + '.csv';
    const result = await downloadFile(fname, '\uFEFF' + csv, 'text/csv');
    if (result.success) showModal('Sukses', '✓ Export CSV: ' + addresses.length + ' alamat');
}'''

NEW_EXPORT_SHORT = r'''async function exportShortCSV(){
    const nf = (document.getElementById('short-export-name').value || '').toLowerCase().trim();
    const ds = document.getElementById('short-export-date-start').value;
    const de = document.getElementById('short-export-date-end').value;
    const addresses = await getAllAddresses();
    let fl = addresses.filter(a => {
        if (nf) { const nm = (a.recipient_name||'').toLowerCase().includes(nf) || (a.whatsapp||'').includes(nf); if (!nm) return false; }
        if (ds || de) { const vd = a.last_visit_at || a.created_at; if (ds && vd < ds+'T00:00:00') return false; if (de && vd > de+'T23:59:59') return false; }
        return true;
    });
    if (fl.length === 0) { showModal('Info', '⚠️ Tidak ada data'); return; }
    const h = ['id','nama','no_wa','gang','nomor','rt','rw','kelurahan','alamat','latitude','longitude','patokan','status_pembayaran','masalah','tipe_lokasi','visit_count','kunjungan_terakhir','catatan'];
    const rows = fl.map(a => [a.id,a.recipient_name,a.whatsapp||'',a.gang,a.house_number,a.rt||'',a.rw||'',a.kelurahan||'',a.address,a.latitude,a.longitude,a.landmark,a.payment_status,(a.problem_tags||[]).join('; '),a.location_type,a.visit_count||1,formatDate(a.last_visit_at||a.created_at),a.description]);
    let csv = h.join(',') + '\n';
    rows.forEach(r => { csv += r.map(c => (typeof c==='string'&&(c.includes(',')||c.includes('"'))) ? '"'+c.replace(/"/g,'""')+'"' : (c||'')).join(',') + '\n'; });
    let fn = 'kurir-q-export';
    if (nf) fn += '-' + nf;
    if (ds) fn += '-from-' + ds;
    if (de) fn += '-to-' + de;
    const result = await downloadFile(fn + '.csv', '\uFEFF' + csv, 'text/csv');
    if (result.success) showModal('Sukses', '✓ ' + fl.length + ' data diexport');
}'''

NEW_EXPORT_TEMPLATE = r'''function exportCSVTemplate(){
    const t = 'id,nama,no_wa,gang,nomor,rt,rw,kelurahan,alamat,patokan,status_pembayaran,tipe_lokasi,catatan\n,Yeyen,(+62)085156395041,,,001,002,Cipedak,"Jalan Aselih No.52",,,,\n,Pak Budi,628123456789,Gang 4,27,003,004,Cipedak,"Gang 4 No.27",Pagar hitam,cod,,\n';
    downloadFile('kurir-q-template.csv', '\uFEFF' + t, 'text/csv').then(r => {
        if (r.success) showModal('Template CSV', 'Format CSV:\n\nKolom WAJIB:\n• nama\n\nKolom OPSIONAL:\n• id, no_wa, gang, nomor, rt, rw\n• kelurahan, alamat, patokan\n• status_pembayaran, tipe_lokasi, catatan\n\n💡 Nomor WA mobile: 628xxxxxxxxx\n💡 Nomor telpon rumah: 6221xxx (bukan WA)');
    });
}'''

# Apply patches
if replace_function('exportJSON', NEW_EXPORT_JSON):
    changes.append('exportJSON (share fallback)')
if replace_function('exportCSV', NEW_EXPORT_CSV):
    changes.append('exportCSV (share fallback)')
if replace_function('exportShortCSV', NEW_EXPORT_SHORT):
    changes.append('exportShortCSV (share fallback)')

# exportCSVTemplate tidak async, pakai find_replace
old = "function exportCSVTemplate(){"
if old in html and 'async function exportCSVTemplate' not in html:
    # Ganti seluruh fungsi exportCSVTemplate
    start = html.find('function exportCSVTemplate(')
    if start != -1:
        brace = html.find('{', start)
        if brace != -1:
            depth, i = 0, brace
            while i < len(html):
                if html[i] == '{': depth += 1
                elif html[i] == '}':
                    depth -= 1
                    if depth == 0: break
                i += 1
            html = html[:start] + NEW_EXPORT_TEMPLATE + html[i+1:]
            changes.append('exportCSVTemplate (share fallback)')

# Tambah helper downloadFile & showManualCopyModal setelah function terakhir sebelum exportJSON
if 'async function downloadFile(' not in html:
    # Cari fungsi exportJSON lama (yang akan dipanggil), sisipkan helper SEBELUMNYA
    anchor = "async function exportJSON()"
    if anchor in html:
        idx = html.find(anchor)
        html = html[:idx] + NEW_DOWNLOAD_HELPER + '\n' + html[idx:]
        changes.append('downloadFile + showManualCopyModal + copyManualContent')

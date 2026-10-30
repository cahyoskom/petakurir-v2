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

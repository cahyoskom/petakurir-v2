#!/usr/bin/env python3
"""Kurir-Q index.html Patcher — ROBUST & IDEMPOTENT"""
import os, re, sys

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

EMOJI  = os.environ.get('APP_EMOJI', '🛵')
BG     = os.environ.get('ICON_BG', '#2563eb')
NAME   = os.environ.get('APP_NAME', 'Kurir-Q')
BG_URL = BG.replace('#', '%23')
changes = []
skipped = []


def replace_function(name, new_code):
    """Replace fungsi JS pakai brace-matching — cocok apapun isinya"""
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
    # Cek apakah sudah versi baru (skip kalau sama)
    current = html[start:i+1]
    if 'validateWAFormat' in current and 'validateWAFormat' in new_code:
        return 'already'  # sudah dipatch, tidak perlu lagi
    html = html[:start] + new_code + html[i+1:]
    return True


def regex_replace(name, pattern, replacement_fn, marker_in_result=None):
    """Replace pakai regex — cocok untuk emoji/warna apapun"""
    global html
    if marker_in_result and marker_in_result in html:
        skipped.append(f'{name} (sudah ada)')
        return False
    new_html, n = re.subn(pattern, replacement_fn, html, count=1)
    if n == 0:
        return False
    html = new_html
    changes.append(name)
    return True


# ============================================================
# PATCH WAJIB: Normalisasi WA (fungsi baru)
# ============================================================
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

r = replace_function('normalizeWhatsApp', NEW_WA)
if r is True:
    changes.append('WA normalize + validate + import')
elif r == 'already':
    skipped.append('WA normalize (sudah ada)')
else:
    print('❌ CRITICAL: fungsi normalizeWhatsApp tidak ditemukan!')
    sys.exit(1)


# ============================================================
# PATCH WAJIB: analyzeWhatsAppNumbers
# ============================================================
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

r = replace_function('analyzeWhatsAppNumbers', NEW_ANALYZE)
if r is True:
    changes.append('WA analyze')
elif r == 'already':
    skipped.append('WA analyze (sudah ada)')


# ============================================================
# PATCH: CSV import call — pakai regex fleksibel
# ============================================================
if 'importNormalizeWA(waRaw)' in html:
    skipped.append('CSV import call (sudah ada)')
else:
    # Match apapun bentuknya: whatsapp:waRaw?normalizeWhatsApp(waRaw):''
    pattern = r"whatsapp\s*:\s*waRaw\s*\?\s*normalizeWhatsApp\s*\(\s*waRaw\s*\)\s*:\s*['\"]['\"]"
    replacement = "whatsapp:(function(){const r=importNormalizeWA(waRaw);return r.wa;})()"
    new_html, n = re.subn(pattern, replacement, html, count=1)
    if n > 0:
        html = new_html
        changes.append('CSV import call')
    else:
        # Fallback: cari "normalizeWhatsApp(waRaw)" apapun bentuknya
        pattern2 = r"normalizeWhatsApp\(waRaw\)"
        if pattern2 in html:
            html = html.replace('normalizeWhatsApp(waRaw)', 'importNormalizeWA(waRaw).wa')
            changes.append('CSV import call (fallback)')


# ============================================================
# PATCH: warnings lengkap — idempotent
# ============================================================
if 'TELEPON RUMAH (tidak bisa WA)' in html:
    skipped.append('warnings (sudah ada)')
else:
    # Cari baris lama dengan regex fleksibel
    old_pattern = r"if\s*\(\s*issues\.fixedLine\.length\s*>\s*0\s*\)\s*warnings\.push\s*\(\s*`[^`]*fixedLine[^`]*`\s*\)\s*;"
    new_block = '''if(issues.valid.length>0)warnings.push(`✅ ${issues.valid.length} mobile valid`);
    if(issues.double62.length>0)warnings.push(`🔁 ${issues.double62.length} nomor "62-62" dobel`);
    if(issues.leading62_0.length>0)warnings.push(`⚠️ ${issues.leading62_0.length} nomor "62-0..."`);
    if(issues.fixedLine.length>0)warnings.push(`📞 ${issues.fixedLine.length} TELEPON RUMAH (tidak bisa WA)`);
    if(issues.tooShort.length>0)warnings.push(`📏 ${issues.tooShort.length} terlalu pendek`);
    if(issues.tooLong.length>0)warnings.push(`📏 ${issues.tooLong.length} terlalu panjang`);
    if(issues.unknown.length>0)warnings.push(`❓ ${issues.unknown.length} format aneh`);
    if(issues.empty.length>0)warnings.push(`📭 ${issues.empty.length} kosong`);'''
    new_html, n = re.subn(old_pattern, new_block, html, count=1)
    if n > 0:
        html = new_html
        changes.append('warnings lengkap')


# ============================================================
# PATCH: Emoji — pakai regex fleksibel (cocok emoji apapun)
# ============================================================
def patch_emoji(name, pattern, marker=None):
    """Ganti emoji apapun di context tertentu"""
    global html
    if marker and marker in html:
        skipped.append(f'{name} (sudah {marker})')
        return
    new_html, n = re.subn(pattern, lambda m: m.group(1) + EMOJI + m.group(3), html, count=1)
    if n > 0:
        html = new_html
        changes.append(name)

# Boot splash: cocok emoji apapun antara ">...:</div>"
patch_emoji(
    'boot emoji',
    r'(animation:bootPulse 1\.5s infinite">)([^<]+)(</div>)',
    marker=f'infinite">{EMOJI}</div>'
)

# Header: cocok emoji apapun + nama apapun
patch_emoji(
    'header emoji',
    r'(<header><h1>)([^<]+?)(\s+' + re.escape(NAME) + r'</h1>)',
    marker=f'<h1>{EMOJI} {NAME}</h1>'
)

# Apple icon: cocok emoji apapun
patch_emoji(
    'apple icon emoji',
    r"(dominant-baseline='middle'>)([^<]+)(</text>)",
    marker=f"middle'>{EMOJI}</text>"
)


# ============================================================
# PATCH: Warna (opsional)
# ============================================================
if BG.lower() != '#2563eb':
    # boot BG
    if f'#boot-splash{{position:fixed;inset:0;background:{BG};' not in html:
        old = '#boot-splash{position:fixed;inset:0;background:#2563eb;'
        if old in html:
            html = html.replace(old, f'#boot-splash{{position:fixed;inset:0;background:{BG};')
            changes.append('boot BG')
    
    # theme-color
    new_html, n = re.subn(r'<meta name="theme-color" content="#[0-9a-fA-F]{6}">',
                          f'<meta name="theme-color" content="{BG}">', html)
    if n > 0:
        html = new_html
        changes.append('theme-color')
    
    # apple icon BG
    if BG_URL not in html and "fill='%232563eb'" in html:
        html = html.replace("fill='%232563eb'", f"fill='{BG_URL}'")
        changes.append('apple BG')


# ============================================================
# SIMPAN
# ============================================================
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\n" + "=" * 60)
print(f"📊 Total patch BERHASIL: {len(changes)}")
for c in changes:
    print(f"  ✅ {c}")
if skipped:
    print(f"\n⏭️  Dilewati (sudah ada): {len(skipped)}")
    for s in skipped:
        print(f"  ⏭️  {s}")
print("=" * 60)

# Kalau WA normalisasi sukses → anggap sukses (critical sudah masuk)
if len(changes) >= 1 or len(skipped) >= 1:
    print("\n✅ Selesai. Patch WA normalisasi SUDAH masuk index.html")
    sys.exit(0)
else:
    print("\n❌ TIDAK ADA patch berhasil — cek struktur index.html!")
    sys.exit(1)

/*QUICKSAVE-v1*/
async function kqQuickSave(){
    if(!navigator.geolocation){showModal('Error','GPS tidak tersedia di perangkat ini');return;}
    showLoading('Mengambil lokasi GPS...');
    let lat=null,lng=null;
    try{
        const pos=await new Promise((res,rej)=>{
            navigator.geolocation.getCurrentPosition(res,rej,{enableHighAccuracy:true,timeout:15000,maximumAge:0});
        });
        lat=pos.coords.latitude;
        lng=pos.coords.longitude;
        hideLoading();
    }catch(e){
        hideLoading();
        showConfirmModal(
            'GPS Gagal',
            'Gagal ambil lokasi: '+(e.message||'unknown')+'\n\nTetap foto tanpa lokasi? (bisa diisi nanti)',
            ()=>{openQuickSaveCamera(null,null);}
        );
        return;
    }
    openQuickSaveCamera(lat,lng);
}

function openQuickSaveCamera(lat,lng){
    const input=document.getElementById('kqQuickPhoto');
    if(!input){showModal('Error','Input foto tidak ditemukan');return;}
    input.value='';
    input.onchange=async function(e){
        const file=e.target.files&&e.target.files[0];
        if(!file)return;
        showLoading('Menyimpan foto...');
        try{
            const compressed=await compressImage(file,900,0.72);
            if(!compressed)throw new Error('Gagal memproses foto');
            let uLat=lat,uLng=lng;
            if(uLat===null||uLng===null){
                if(currentLocation&&typeof currentLocation.latitude==='number'){
                    uLat=currentLocation.latitude;
                    uLng=currentLocation.longitude;
                }else{
                    uLat=0;uLng=0;
                }
            }
            const now=new Date();
            const ts=now.toISOString();
            const label=now.toLocaleString('id-ID',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
            const nameDef='Foto '+label;
            const addr={
                recipient_name:nameDef,
                latitude:uLat,
                longitude:uLng,
                whatsapp:'',gang:'',house_number:'',rt:'',rw:'',
                kelurahan:'',address:'',landmark:'',resi:'',
                description:'Quick save '+label,
                payment_status:'belum',
                location_type:'jelas',
                problem_tags:[],
                raw_voice_note:'',
                visit_count:1,
                last_visit_at:ts,
                delivery_status:'belum selesai',
                recipients:[{name:nameDef,status:'belum selesai',added_at:ts}],
                history:[{date:ts,status:'belum selesai',notes:'Quick save foto'}],
                photos:[compressed],
                photo:compressed,
                photo_ref:'quick-'+Date.now()+'.jpg'
            };
            await saveAddress(addr);
            hideLoading();
            updateMapMarkers();
            updateAddressList();
            toast('Foto tersimpan di '+uLat.toFixed(5)+', '+uLng.toFixed(5),'success');
            setTimeout(()=>showAddressDetail(addr.id),300);
        }catch(err){
            hideLoading();
            showModal('Error','Gagal simpan: '+err.message);
        }
    };
    input.click();
}


async function kqQuickPhotoFor(addrId){
    if(!addrId){showModal("Error","ID alamat kosong");return;}
    const a=await getAddressById(addrId);
    if(!a){showModal("Error","Alamat tidak ditemukan");return;}
    const existing=extractAddressPhotos(a);
    if(existing.length>=2){
        showConfirmModal("Foto Sudah Ada ("+existing.length+")","Alamat sudah punya "+existing.length+" foto. Ganti foto lama?",
            function(){kqQuickPhotoCapture(addrId)});
        return;
    }
    kqQuickPhotoCapture(addrId);
}

function kqQuickPhotoCapture(addrId){
    const input=document.getElementById("kqQuickPhoto");
    if(!input){showModal("Error","Input foto tidak ada");return;}
    input.value="";
    input.onchange=async function(e){
        const file=e.target.files&&e.target.files[0];
        if(!file)return;
        showLoading("Menyimpan foto...");
        try{
            const compressed=await compressImage(file,900,0.72);
            if(!compressed)throw new Error("Gagal proses foto");
            const a=await getAddressById(addrId);
            if(!a)throw new Error("Alamat tidak ditemukan");
            let photos=extractAddressPhotos(a);
            if(photos.length===0){photos=[compressed];}
            else if(photos.length===1){photos=[photos[0],compressed];}
            else{photos=[compressed,photos[1]];}
            a.photos=photos;
            a.photo=photos[0];
            a.updated_at=new Date().toISOString();
            if(!a.history)a.history=[];
            a.history.push({date:new Date().toISOString(),status:"foto",notes:"Quick foto via card"});
            await saveAddress(a);
            hideLoading();
            updateMapMarkers();
            updateAddressList();
            toast("Foto tersimpan: "+a.recipient_name,"success");
            if(currentDetailId===addrId)setTimeout(function(){showAddressDetail(addrId)},200);
        }catch(err){
            hideLoading();
            showModal("Error","Gagal: "+err.message);
        }
    };
    input.click();
}


/*QSAVE-FIX-v1*/
function kqShowLoading(m){
  var el=document.getElementById("kqQuickLoading");
  if(!el){
    el=document.createElement("div");
    el.id="kqQuickLoading";
    el.style.cssText="position:fixed;inset:0;background:rgba(0,0,0,.55);display:none;align-items:center;justify-content:center;flex-direction:column;gap:14px;z-index:9999;color:#fff;font-family:sans-serif";
    var sp=document.createElement("div");
    sp.style.cssText="width:44px;height:44px;border:4px solid rgba(255,255,255,.25);border-top-color:#fff;border-radius:50%;animation:kqspin 1s linear infinite";
    var tx=document.createElement("div");
    tx.id="kqQuickLoadingText";
    tx.style.cssText="font-size:13px;font-weight:600";
    el.appendChild(sp);el.appendChild(tx);
    document.body.appendChild(el);
    if(!document.getElementById("kqspin-style")){
      var st=document.createElement("style");
      st.id="kqspin-style";
      st.textContent="@keyframes kqspin{to{transform:rotate(360deg)}}";
      document.head.appendChild(st);
    }
  }
  var t2=document.getElementById("kqQuickLoadingText");
  if(t2)t2.textContent=m||"Memproses...";
  el.style.display="flex";
}
function kqHideLoading(){
  var el=document.getElementById("kqQuickLoading");
  if(el)el.style.display="none";
}
window.kqQuickSave=async function(){
  kqShowLoading("Mengambil lokasi GPS...");
  var lat=null,lng=null;
  try{
    if(navigator.geolocation){
      var pos=await new Promise(function(res,rej){
        navigator.geolocation.getCurrentPosition(res,rej,{enableHighAccuracy:true,timeout:8000,maximumAge:30000});
      });
      lat=pos.coords.latitude;lng=pos.coords.longitude;
    }
  }catch(e){
    console.warn("QS GPS err:",e&&e.message);
    if(typeof currentLocation==="object"&&currentLocation&&typeof currentLocation.latitude==="number"&&currentLocation.latitude!==0){
      lat=currentLocation.latitude;lng=currentLocation.longitude;
    }
  }
  kqHideLoading();
  openQuickSaveCamera(lat,lng);
};
window.openQuickSaveCamera=function(lat,lng){
  var input=document.getElementById("kqQuickPhoto");
  if(!input){alert("Input foto tidak ditemukan");return;}
  input.value="";
  input.onchange=async function(e){
    var f=e.target.files&&e.target.files[0];if(!f)return;
    kqShowLoading("Menyimpan foto...");
    try{
      var compressed=await compressImage(f,900,0.72);
      if(!compressed)throw new Error("Gagal proses foto");
      var uLat=lat,uLng=lng;
      if(uLat===null||uLng===null){
        if(typeof currentLocation==="object"&&currentLocation&&typeof currentLocation.latitude==="number"){uLat=currentLocation.latitude;uLng=currentLocation.longitude;}
        else{uLat=0;uLng=0;}
      }
      var now=new Date(),ts=now.toISOString();
      var label=now.toLocaleString("id-ID",{day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"});
      var nameDef="Foto "+label;
      var addr={recipient_name:nameDef,latitude:uLat,longitude:uLng,whatsapp:"",gang:"",house_number:"",rt:"",rw:"",kelurahan:"",address:"",landmark:"",resi:"",description:"Quick save "+label,payment_status:"belum",location_type:"jelas",problem_tags:[],raw_voice_note:"",visit_count:1,last_visit_at:ts,delivery_status:"belum selesai",recipients:[{name:nameDef,status:"belum selesai",added_at:ts}],history:[{date:ts,status:"belum selesai",notes:"Quick save foto"}],photos:[compressed],photo:compressed,photo_ref:"quick-"+Date.now()+".jpg"};
      await saveAddress(addr);
      kqHideLoading();
      if(typeof updateMapMarkers==="function")updateMapMarkers();
      if(typeof updateAddressList==="function")updateAddressList();
      if(typeof toast==="function")toast("Foto tersimpan","success");
      setTimeout(function(){if(typeof showAddressDetail==="function")showAddressDetail(addr.id);},300);
    }catch(err){kqHideLoading();alert("Gagal: "+err.message);}
  };
  input.click();
};

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

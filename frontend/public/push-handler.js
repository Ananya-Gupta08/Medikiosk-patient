self.addEventListener('push',event=>{
  let data={title:'Medicine reminder',body:'It is time for your medicine.',url:'/'}
  try{if(event.data)data={...data,...event.data.json()}}catch{/* use privacy-safe fallback */}
  event.waitUntil(self.registration.showNotification(data.title,{body:data.body,icon:'/icon.svg',badge:'/icon.svg',tag:'medicine-reminder',data:{url:data.url}}))
})
self.addEventListener('notificationclick',event=>{
  event.notification.close()
  event.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(windows=>{const existing=windows.find(client=>'focus'in client);return existing?existing.focus():clients.openWindow(event.notification.data?.url||'/')}))
})

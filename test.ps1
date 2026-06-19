$response = Invoke-RestMethod -Uri "https://smart-bazaar-i161.onrender.com/api/auth/login" -Method Post -Body (@{email="admin@smartbazaar.com";password="password"} | ConvertTo-Json) -ContentType "application/json" -ErrorAction Stop
Write-Output $response

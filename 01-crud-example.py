from dotenv import load_dotenv
load_dotenv()

import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)

# Sign-up
user = supabase.auth.sign_up({ "email": users_email, "password": users_password })

# Sign-in
user = supabase.auth.sign_in_with_password({ "email": users_email, "password": users_password })

# Insert Data
data = supabase.table("countries").insert({"name":"Germany"}).execute()
# Assert we pulled real data.
assert len(data.data) > 0


# Select Data
data = supabase.table("countries").select("*").eq("country", "IL").execute()
# Assert we pulled real data.
assert len(data.data) > 0


# Update Data
data = supabase.table("countries").update({"country": "Indonesia", "capital_city": "Jakarta"}).eq("id", 1).execute()


# Update data with duplicate keys
country = {
  "country": "United Kingdom",
  "capital_city": "London" # This was missing when it was added
}
data = supabase.table("countries").upsert(country).execute()
assert len(data.data) > 0

# Delete Data
data = supabase.table("countries").delete().eq("id", 1).execute()

# Call Edge Functions
def test_func():
  try:
    resp = supabase.functions.invoke("hello-world", invoke_options={'body':{}})
    return resp
  except (FunctionsRelayError, FunctionsHttpError) as exception:
    err = exception.to_dict()
    print(err.get("message"))

# Download a file from Storage
bucket_name: str = "photos"
data = supabase.storage.from_(bucket_name).download("photo1.png")

# Upload a file
bucket_name: str = "photos"
new_file = getUserFile()
data = supabase.storage.from_(bucket_name).upload("/user1/profile.png", new_file)

# Remove a file
bucket_name: str = "photos"
data = supabase.storage.from_(bucket_name).remove(["old_photo.png", "image5.jpg"])

# List all files
bucket_name: str = "charts"
data = supabase.storage.from_(bucket_name).list()

# Move and rename files
bucket_name: str = "charts"
old_file_path: str = "generic/graph1.png"
new_file_path: str = "important/revenue.png"
data = supabase.storage.from_(bucket_name).move(old_file_path, new_file_path)
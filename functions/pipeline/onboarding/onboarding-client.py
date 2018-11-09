import requests
import json
import pg8000

# The following mock client imitates the CLI during the onboarding scenario for new images.
# The CLI uploads images to a temporary blob store, then gets a list of URLs to those images and
# passes it to an HTTP trigger function, which calls the DAL to create rows in the database.

print("\nTest client for CLI Onboarding scenario")
print('-' * 40)

# functionURL = "https://onboardinghttptrigger.azurewebsites.net/api/onboarding?code=lI1zl4IhiHcOcxTS85RsE7yZJXeNRxnr7tXSO1SrLWdpiN0W6hT3Jw=="
functionURL = "http://localhost:7071/api/onboarding"

urlList = { "imageUrls": ["http://www.whitneyway.com/Images/15/2017%20Puppies%20in%20Easter%20basket%204-16-17_800.JPG",
                         "http://allpetcages.com/wp-content/uploads/2017/06/puppy-whelping-box.jpg",
                         "http://78.media.tumblr.com/eea2f882ec08255e40cecaf8ca1d4543/tumblr_nmxjbjIK141qi4ucgo1_500.jpg"] }

headers = {"Content-Type": "application/json"}

print("Now executing POST request to onboard images...to:")
print("Function URL: " + functionURL)
print("Headers:")
for key, value in headers.items():
    print("\t" + key + ": " + value)
response = requests.post(url=functionURL, headers=headers, json=urlList)
print("Completed POST request.")

raw_response = response.text
response_array = raw_response.split(", ")
response_output = "\n".join(response_array)

print(f"Response status code: {response.status_code}")
print(f"Response string: {response_output}")
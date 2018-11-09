import os
import logging
import azure.functions as func
from shutil import copyfile
from ..shared import db_access as DB_Access
from ..shared import db_access_v2 as DB_Access_V2
# from ..shared import db_provider

default_db_host = ""
default_db_name = ""
default_db_user = ""
default_db_pass = ""

# Testing URL for what will be permanent (destination) blob storage
DESTINATION_DIRECTORY = "http://akaonboardingstorage.blob.core.windows.net/aka-testimagecontainer"

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        req_body = req.get_json()
        logging.error(req.get_json())
        url_list = req_body["imageUrls"]
        # url_string = (", ".join(url_list))    # For testing output response
    except ValueError:
        print("Unable to decode JSON body")
        return func.HttpResponse("Unable to decode POST body", status_code=400)

    logging.error(req_body)

    # Testing HttpResponse to show that JSON URL list was received and parsed correctly
    # Note: If used, comment out all below this return line
    # return func.HttpResponse(url_string, status_code=200)

    # Build list of image objects to pass to DAL for insertion into DB.
    image_object_list = []
    image_name_list = []
    for url in url_list:
        # Split original image name from URL
        original_filename = url.split("/")[-1]
        image_name_list.append(original_filename)
        # Create ImageInfo object (def in db_access.py)
        # Note: For testing, default image height/width are set to 50x50
        image = DB_Access.ImageInfo(original_filename, url, 50, 50)
        # Append image object to the list
        image_object_list.append(image)

    # Get database connection
    db_config = DB_Access_V2.DatabaseInfo(os.getenv('DB_HOST', default_db_host), os.getenv('DB_NAME', default_db_name), os.getenv('DB_USER', default_db_user), os.getenv('DB_PASS', default_db_pass))
    data_access = DB_Access_V2.ImageTagDataAccess(DB_Access_V2.PostGresProvider(db_config))

    # Create user id
    user_id = data_access.create_user(DB_Access_V2.getpass.getuser())
    logging.info("The user id for '{0}' is {1}".format(DB_Access_V2.getpass.getuser(),user_id))

    # Add new images to the database, and retrieve a dictionary ImageId's mapped to ImageUrl's
    image_id_url_map = data_access.add_new_images(image_object_list,user_id)

    # Copy over images to permanent blob store
    permanent_url_list = []
    for key, value in image_id_url_map.items():
        file_extension = os.path.splitext(value)[1]
        permanent_storage_path = DESTINATION_DIRECTORY + "/" + key + file_extension
        copyfile(value, permanent_storage_path)
        permanent_url_list.append(permanent_storage_path)
    logging.info("Done copying images to permanent blob storage.")

    # Construct response string of permanent URLs
    # TODO: Use update function from DAL to update image locations in DB
    permanent_url_string = (", ".join(permanent_url_list))    # For testing output response

    # Return string containing list of URLs to images in permanent blob storage
    return func.HttpResponse(permanent_url_string, status_code=200)

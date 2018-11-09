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
    
    # TODO: Add check to ensure image URLs sent by client are all unique.

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
    # Verbose logging for testing:
    # logging.info("DB_HOST = " + os.getenv('DB_HOST'))
    # logging.info("DB_NAME = " + os.getenv('DB_NAME'))
    # logging.info("DB_USER = " + os.getenv('DB_USER'))
    # logging.info("DB_PASS = " + os.getenv('DB_PASS'))

    logging.info("Now connecting to database...")
    db_config = DB_Access_V2.DatabaseInfo(os.getenv('DB_HOST', default_db_host), os.getenv('DB_NAME', default_db_name), os.getenv('DB_USER', default_db_user), os.getenv('DB_PASS', default_db_pass))
    data_access = DB_Access_V2.ImageTagDataAccess(DB_Access_V2.PostGresProvider(db_config))
    logging.info("Connected.")

    # Create user id
    user_id = data_access.create_user(DB_Access_V2.getpass.getuser())
    logging.info("The user id for '{0}' is {1}".format(DB_Access_V2.getpass.getuser(),user_id))

    # Add new images to the database, and retrieve a dictionary ImageId's mapped to ImageUrl's
    image_id_url_map = data_access.add_new_images(image_object_list,user_id)

    # Print out dictionary for debugging
    logging.info("Image ID and URL map dictionary:")
    logging.info(image_id_url_map)

    # Copy over images to permanent blob store and save URLs in a list
    permanent_url_list = []
    update_urls_dictionary = {}
    for key, value in image_id_url_map.items():
        image_url = key
        image_id = value
        logging.info("Original image URL: " + image_url)
        logging.info("Image ID: " + str(image_id))
        file_extension = os.path.splitext(image_url)[1]
        logging.info("File extension: " + file_extension)
        permanent_storage_path = DESTINATION_DIRECTORY + "/" + str(image_id) + file_extension
        logging.info("Permanent storage destination path: " + permanent_storage_path)
        logging.info("Now copying file from temporary to permanent storage...")
        copyfile(image_url, permanent_storage_path)
        logging.info("Done.")
        # Add image to the list of images to be returned in the response
        permanent_url_list.append(permanent_storage_path)
        # Add ImageId and permanent storage url to new dictionary to be sent to update function
        update_urls_dictionary[image_id] = permanent_storage_path

    logging.info("Done copying images to permanent blob storage.")

    logging.info("Now updating permanent URLs in the DB...")
    data_access.update_image_urls(update_urls_dictionary, user_id)
    logging.info("Done.")

    # Construct response string of permanent URLs
    permanent_url_string = (", ".join(permanent_url_list))

    # Return string containing list of URLs to images in permanent blob storage
    return func.HttpResponse("The following images should now be added to the DB and exist in permanent blob storage: " 
        + permanent_url_string, status_code=200)

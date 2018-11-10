import os
import logging
import azure.functions as func
from ..shared import db_access_v2 as DB_Access_V2
from azure.storage.blob import BlockBlobService, ContentSettings

default_db_host = ""
default_db_name = ""
default_db_user = ""
default_db_pass = ""

# TODO: Make environment variables?
storage_account_name = ""
storage_account_key = ""
source_container_name = ""
destination_container_name = ""

# Testing URL for what will be permanent (destination) blob storage
# TODO: Make environment variable
DESTINATION_DIRECTORY = "http://akaonboardingstorage.blob.core.windows.net/aka-testimagecontainer"

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        req_body = req.get_json()
        logging.error(req.get_json())
        url_list = req_body["imageUrls"]
    except ValueError:
        print("Unable to decode JSON body")
        return func.HttpResponse("Unable to decode POST body", status_code=400)

    logging.error(req_body)

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
        # TODO: Figure out where actual height/width need to come from
        image = DB_Access_V2.ImageInfo(original_filename, url, 50, 50)
        # Append image object to the list
        image_object_list.append(image)

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
        original_image_url = key
        original_filename = url.split("/")[-1]
        image_id = value
        logging.info("Original image URL: " + original_image_url)
        logging.info("Original image name: " + original_filename)
        logging.info("Image ID: " + str(image_id))
        file_extension = os.path.splitext(original_image_url)[1]
        logging.info("File extension: " + file_extension)
        new_blob_name = (str(image_id) + file_extension)
        logging.info("New blob name: " + new_blob_name)
        permanent_storage_path = DESTINATION_DIRECTORY + "/" + new_blob_name
        logging.info("Now copying file from temporary to permanent storage...")
        logging.info("Source URL: " + original_image_url)
        logging.info("Destination URL: " + permanent_storage_path)

        blob_service = BlockBlobService(account_name=storage_account_name, 
                                    account_key=storage_account_key)
        blob_name = original_filename
        copy_from_container = source_container_name
        copy_to_container = destination_container_name

        blob_url = blob_service.make_blob_url(copy_from_container, blob_name)

        blob_service.copy_blob(copy_to_container, new_blob_name, blob_url)

        # Delete the file from temp storage once it's been copied
        # TODO: Test
        # blob_service.delete_blob(copy_from_container, blob_name)

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

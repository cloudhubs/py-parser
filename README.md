# py-parser

Python Source Code Parser

## How To Install:
1. Create a local virtual environment for the project to prevent polluting your environment:
Run this command in the project directory:
    ```shell script
     python3 -m venv venv
   ```
   
2. Activate the venv:
  ```shell script
     source venv/bin/activate
  ```

3. Install required dependencies in the virtual environment
  ```shell script
    pip install -r requirements.txt
  ```

4. Run flask application
```shell script
  export FLASK_APP=src/app
  flask run
```
    
    
5. Test that application is running: Assuming the project we
```shell script
curl --request GET --url http://localhost:5000
```
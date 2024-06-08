from app import create_app
#from app import main

app = create_app()
#app.register_blueprint(main)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

"""Register API groups without application-global business state."""


def register_api(app) -> None:
    from app.api import admin, auth, cases, files, orders, products, social

    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(products.bp)
    app.register_blueprint(files.bp)
    app.register_blueprint(orders.bp)
    app.register_blueprint(social.bp)
    app.register_blueprint(cases.bp)

from flask import url_for
import click

from pipet import app
from pipet.models import db, Organization, User


@app.cli.command()
@click.option('--email', prompt="Email")
@click.option('--name', prompt="Organization Name")
def createuser(email, name):
    org = Organization(name=name)
    db.session.add(org)
    db.session.commit()
    user = User(email=email, organization=org)
    db.session.add(user)
    db.session.commit()


@app.cli.command()
@click.option('--email', prompt="Email")
def login(email):
    user = User.query.filter_by(email=email).first()
    if user:
        user.refresh_validation_hash()
        db.session.add(user)
        db.session.commit()
        click.echo('Login at %s' %
                   url_for('login_with_validation',
                           validation_hash=user.validation_hash)
                   )
    else:
        click.echo('%s doesn\'t exist. Run `flask createuser`')

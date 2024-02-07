from xml.etree.ElementTree import tostring

from wtforms import Form, StringField, IntegerField, validators


class OrderForm(Form):
    zip_code = StringField('zip_code', [validators.DataRequired(), validators.Length(min=6, max=6)])
    city = StringField('city', [validators.DataRequired(), validators.Length(max=45)])
    address = StringField('address', [validators.DataRequired(), validators.Length(max=64)])

    def isZipCode(self, code):
        i = 0
        for char in code:
            if i == 2 and char == '-':
                continue
            if not char.isdigit():
                return False

            i += 1

        return True

    def isCity(self, city):
        for char in city:
            if not char.isalpha():
                return False

        return True

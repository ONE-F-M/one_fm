from base64 import b64encode
from io import BytesIO

import qrcode


def get_qr_code(data: str) -> str:
	'''
		The QR code will work flawlessly in print preview and PDF. The print format is very simple.
		It uses the data from QR Code like this:

		<p>QR Code stored in field <i>QR Code</i>:</p>
		<img src="{{ doc.qr_code }}"/>

		The field qr_code(Samll Text) set from this method get_qr_code(str)

		The QR code can show in the document by having an image field(set options as qr_code field)

		For cases when we need dynamic QR codes, that are not stored in the document,
		we can generate them ad-hoc by calling get_qr_code in the print format:

		<p>QR Code generated ad-hoc:</p>
		<img src="{{ get_qr_code('Hello World!') }}" alt="Hello World!"/>

		We achieved this by adding the get_qr_code() method to the jinja configuration in our hooks.py file, like this:

		jinja = {
			"methods": [
				"qr_demo.qr_code.get_qr_code"
			],
		}
	'''
	qr_code_bytes = get_qr_code_bytes(data, format="PNG")
	base_64_string = bytes_to_base64_string(qr_code_bytes)

	return add_file_info(base_64_string)


def add_file_info(data: str) -> str:
	"""Add info about the file type and encoding.

	This is required so the browser can make sense of the data."""
	return f"data:image/png;base64, {data}"


def get_qr_code_bytes(data, format: str) -> bytes:
	"""Create a QR code and return the bytes."""
	img = qrcode.make(data)

	buffered = BytesIO()
	img.save(buffered, format=format)

	return buffered.getvalue()


def bytes_to_base64_string(data: bytes) -> str:
	"""Convert bytes to a base64 encoded string."""
	return b64encode(data).decode("utf-8")

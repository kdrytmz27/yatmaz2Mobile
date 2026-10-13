const fs = require('fs');
let code = fs.readFileSync('clientsource/EterImageLib/TGAImage.cpp', 'utf8');

const replacement = `bool CTGAImage::LoadFromMemory(int iSize, const BYTE* c_pbMem)
{
	int x, y, comp;
	unsigned char *data = stbi_load_from_memory((const stbi_uc*)c_pbMem, iSize, &x, &y, &comp, 4);
	if (!data)
		return false;

	memset(&m_Header, 0, sizeof(m_Header));
	m_Header.imgType = 2;
	m_Header.width = (short)x;
	m_Header.height = (short)y;
	m_Header.colorBits = 32;
	m_Header.desc = 0x08;

	CImage::Create(x, y);

	DWORD* pdwDest = GetBasePointer();
	UINT hxw = x * y;
	
	for (UINT i = 0; i < hxw; ++i)
	{
		BYTE r = data[i * 4 + 0];
		BYTE g = data[i * 4 + 1];
		BYTE b = data[i * 4 + 2];
		BYTE a = data[i * 4 + 3];
		pdwDest[i] = (a << 24) | (r << 16) | (g << 8) | b;
	}

	stbi_image_free(data);

	if (!(m_Header.desc & IMAGEDESC_TOPLEFT))
		FlipTopToBottom();

	return true;
}

bool CTGAImage::LoadFromDiskFile(const char* c_szFileName)`;

const regex = /bool CTGAImage::LoadFromMemory\(.*?\n\{([\s\S]*?)\nbool CTGAImage::LoadFromDiskFile\(const char\* c_szFileName\)/;
code = code.replace(regex, replacement);

code = '#include "stb_image.h"\n' + code;

fs.writeFileSync('clientsource/EterImageLib/TGAImage.cpp', code);
console.log("Replaced LoadFromMemory successfully!");

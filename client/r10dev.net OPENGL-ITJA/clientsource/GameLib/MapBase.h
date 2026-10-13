#pragma once

class CMapBase : public CScreen
{
public:
	enum EMAPTYPE
	{
		MAPTYPE_INVALID,
		MAPTYPE_INDOOR,
		MAPTYPE_OUTDOOR,
	};

public:
	CMapBase();
	virtual ~CMapBase();

	virtual void	Clear();
	virtual bool	Initialize() = 0;
	virtual bool	Destroy() = 0;
	virtual bool	Load(float x, float y, float z) = 0;

	virtual bool	Update(float fX, float fY, float fZ) = 0;
	virtual void	UpdateAroundAmbience(float fX, float fY, float fZ) = 0;
	virtual float	GetHeight(float fx, float fy) = 0;
	virtual void	OnBeginEnvironment() = 0; // ������ �� �� �ҷ����� ���⼭ Environment�� ���� �ִ� �͵��� ���� �Ѵ�.

	virtual void 	ApplyLight(DWORD dwVersion, const D3DLIGHT8& c_rkLight) = 0;

protected:
	virtual void	OnRender() = 0;
	virtual void	OnSetEnvironmentDataPtr() = 0;	// Environment �����Ͱ� ������ �� �ҷ�����.
	virtual void	OnResetEnvironmentDataPtr() = 0;

public:
	void			Render();
	void			SetEnvironmentDataPtr(const TEnvironmentData* c_pEnvironmentData);
	void			ResetEnvironmentDataPtr(const TEnvironmentData* c_pEnvironmentData);
	bool			Enter();
	bool			Leave();
	bool			IsReady() { return m_bReady; }

	bool			LoadProperty();

	//////////////////////////////////////////////////////////////////////////
	// Setting
	//////////////////////////////////////////////////////////////////////////
	EMAPTYPE GetType() const { return m_eType; }
	void SetType(EMAPTYPE eType) { m_eType = eType; }

	const std::string& GetName() const { return m_strName; }
	void SetName(const std::string& cr_strName) { m_strName = cr_strName; }

	bool IsCopiedMap() const { return m_strParentMapName.length() > 0; }		// "���� �����ʹ� ���� �ִ�" ���� ���ΰ�?
	const std::string& GetParentMapName() const { return m_strParentMapName; }	// ���� �����͸� �����ִ� ���� �̸��� ���� (������� ��� �ʼ��� ���õǾ�� ��)
	const std::string& GetMapDataDirectory() const { return IsCopiedMap() ? m_strParentMapName : m_strName; }

protected:
	EMAPTYPE				m_eType;				// �� ����... ����� Indoor�� Ourdoor�� �ִ�.
	std::string				m_strName;				// �� �̸�. �� �̸��� �� �ĺ��ڰ� �� �� ������?
	std::string				m_strParentMapName;		// ���� ���� �̸�. �� ���� ���õǾ� �ִٸ� ���� ��� �� �����ʹ� ParentMap/* ��ο��� �о�´�. ���� �Ϻθ� �о���� ����� �ʿ���뼭 �н�.
	bool					m_bReady;

	const TEnvironmentData* mc_pEnvironmentData;
};

#ifndef _EL_CPOSTIT_H_
#define _EL_CPOSTIT_H_

// _CPostItMemoryBlock is defined in CPostIt.cpp
class _CPostItMemoryBlock;

/**
 * @class	CPostIt
 * @brief	���ӷ�ó���� ���� Ŭ���̾�Ʈ�� ������ ���� �� Ŭ���̾�Ʈ���� �����ϱ� ���Ͽ� ���Ǵ� Ŭ����
 */
class CPostIt
{
public:
	/**
	 * @brief	CPostIt constructor
	 * @param [in]	szAppName	: ������ �̸��� ����.
	 */
	explicit CPostIt(LPCSTR szAppName);

	/**
	 * @brief	CPostIt destructor
	 */
	~CPostIt(void);

	/**
	 * @brief	CPostIt class���� �����ϰ� �ִ� ����Ÿ�� Ŭ�����忡 �����Ѵ�.
	 */
	BOOL	Flush(void);

	/**
	 * @brief	CPostIt class���� �����ϰ� �ִ� ����Ÿ �� Ŭ�����忡 �ִ� ������ �����.
	 */
	void	Empty(void);

	/**
	 * @brief	����Ÿ�� �о�´�.
	 * @param [in]	lpszKeyName	: �ҷ��� ����Ÿ�� Ű. "KEY" ���� ������ �ִ´�.
	 * @param [in]	lpszData	: �ҷ��� ����Ÿ�� ����
	 * @param [in]	nSize		: lpszData ������ �ִ������
	 */
	BOOL	Get(LPCSTR lpszKeyName, LPSTR lpszData, DWORD nSize);

	/**
	 * @brief	������ ����Ÿ�� �ִ´�.
	 * @param [in]	lpBuffer	: ������ ����Ÿ. "KEY=DATA" ���� ������ �ִ´�.
	 */
	BOOL	Set(LPCSTR lpszData);

	/**
	 * @brief	������ ����Ÿ�� �ִ´�.
	 * @param [in]	lpszKeyName	: ������ ����Ÿ�� Ű. "KEY" ���� ������ �ִ´�.
	 * @param [in]	lpszData	: ������ ����Ÿ. "DATA" ���� ������ �ִ´�.
	 */
	BOOL	Set(LPCSTR lpszKeyName, LPCSTR lpszData);

	/**
	 * @brief	������ ����Ÿ(DWORD)�� �ִ´�.
	 * @param [in]	lpBuffer	: ������ ����Ÿ. "KEY=DATA" ���� ����Ÿ�� �ִ´�.
	 * @param [in]	dwValue		: ������ ����Ÿ. (DWORD)
	 */
	BOOL	Set(LPCSTR lpszKeyName, DWORD dwValue);

	/**
	 * @brief	CPostIt class�� �����Ѵ�. (Ŭ���� constructor�� �̸� ���ڰ� �ֱ� ������, �� �̸��� �����ؾ���)
	 * @param [in]	pPostIt		: Destination class
	 * @param [in]	lpszKeyName	: Destination class's new app-name
	 */
	BOOL	CopyTo(CPostIt* pPostIt, LPCSTR lpszKeyName);

protected:
	BOOL					Init(LPCSTR szAppName);
	void					Destroy(void);

protected:
	BOOL					m_bModified;
	CHAR					m_szClipFormatName[_MAX_PATH];
	_CPostItMemoryBlock* m_pMemoryBlock;
};

#endif /* _EL_CPOSTIT_H_ */

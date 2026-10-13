#ifndef __INC_ETERLIB_THREAD_H__
#define __INC_ETERLIB_THREAD_H__

class CThread
{
public:
	CThread();
	int Create(void* arg);

protected:
	static UINT CALLBACK	EntryPoint(void* pThis);

	virtual UINT			Setup() = 0;				// Execute�� �ҷ����� ���� �ҷ�����.
	virtual UINT			Execute(void* arg) = 0;	// ���� �����尡 �ϴ� ���� ���� ��

	UINT					Run(void* arg);

	void* Arg() const { return m_pArg; }
	void					Arg(void* arg) { m_pArg = arg; }

	HANDLE					m_hThread;

private:
	void* m_pArg;
	unsigned				m_uThreadID;
};

#endif

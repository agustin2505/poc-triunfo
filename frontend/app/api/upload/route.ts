import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL ?? 'http://127.0.0.1:8090'

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const res = await fetch(`${BACKEND}/upload`, { method: 'POST', body: formData })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (err) {
    return NextResponse.json({ detail: String(err) }, { status: 503 })
  }
}

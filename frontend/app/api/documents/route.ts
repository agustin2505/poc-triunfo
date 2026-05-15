import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL ?? 'http://127.0.0.1:8090'

export async function GET(request: NextRequest) {
  const qs = request.nextUrl.searchParams.toString()
  const url = qs ? `${BACKEND}/documents?${qs}` : `${BACKEND}/documents`
  try {
    const res = await fetch(url, { cache: 'no-store' })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (err) {
    return NextResponse.json({ detail: String(err) }, { status: 503 })
  }
}

import axios from 'axios'

import type { CityImage, TravelPlanResponse, TravelRequest } from '../types/travel'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 120000
})

export async function createTripPlan(payload: TravelRequest): Promise<TravelPlanResponse> {
  const { data } = await api.post<TravelPlanResponse>('/api/trips/plan', payload)
  return data
}

export async function getCityImage(city: string): Promise<CityImage> {
  const { data } = await api.get<CityImage>('/api/media/city-image', {
    params: { city }
  })
  return data
}

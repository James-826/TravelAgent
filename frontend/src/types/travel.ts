export type Money = number | string

export interface Location {
  city: string
  district?: string | null
  address?: string | null
  latitude?: number | null
  longitude?: number | null
  amap_adcode?: string | null
  amap_poi_id?: string | null
  label?: string
}

export interface Attraction {
  id: string
  name: string
  location: Location
  category: string
  rating?: number | null
  duration_hours: number
  ticket_price: Money
  tags: string[]
  highlights: string[]
  opening_hours?: string | null
  crowd_level: 'low' | 'medium' | 'high'
  source: string
  map_url?: string | null
}

export interface Hotel {
  id: string
  name: string
  location: Location
  rating?: number | null
  star_level?: number | null
  price_per_night: Money
  amenities: string[]
  suitable_for: string[]
  distance_to_center_km?: number | null
  booking_tip?: string | null
}

export interface Meal {
  id: string
  name: string
  location: Location
  meal_type: 'breakfast' | 'lunch' | 'dinner' | 'snack'
  cuisine: string
  price_per_person: Money
  recommended_dishes: string[]
  rating?: number | null
  reservation_required: boolean
}

export interface WeatherDaily {
  date: string
  location: Location
  condition: string
  temperature_low: number
  temperature_high: number
  wind?: string | null
  humidity?: number | null
  tips: string[]
}

export interface BudgetBreakdown {
  currency: string
  attraction_total: Money
  hotel_total: Money
  meal_total: Money
  transport_total: Money
  buffer_total: Money
  grand_total: Money
}

export interface DayTrip {
  day_index: number
  date?: string | null
  theme: string
  summary: string
  attractions: Attraction[]
  meals: Meal[]
  hotel?: Hotel | null
  weather?: WeatherDaily | null
  transportation: string[]
  estimated_cost: Money
  notes: string[]
  route_points: Location[]
}

export interface TripPlan {
  id: string
  destination: Location
  start_date: string
  end_date: string
  travelers: number
  title: string
  total_days: number
  days: DayTrip[]
  hotels: Hotel[]
  budget: BudgetBreakdown
  assumptions: string[]
  warnings: string[]
  generated_at: string
}

export interface TravelRequest {
  origin: Location
  destination: Location
  start_date: string
  end_date: string
  travelers: number
  budget_level: 'economy' | 'standard' | 'premium'
  interests: string[]
  pace: 'relaxed' | 'balanced' | 'packed'
  hotel_level: 'budget' | 'comfort' | 'luxury'
  dietary_preferences: string[]
  notes?: string | null
}

export interface AgentReport {
  agent_name: string
  status: 'success' | 'partial' | 'failed'
  summary: string
  started_at: string
  finished_at: string
  warnings: string[]
}

export interface TravelPlanResponse {
  request_id: string
  plan: TripPlan
  agents: AgentReport[]
}

export interface CityImage {
  city: string
  configured: boolean
  image_url?: string | null
  thumb_url?: string | null
  alt_description?: string | null
  color?: string | null
  photographer_name?: string | null
  photographer_url?: string | null
  photo_url?: string | null
  source: 'unsplash' | 'fallback'
}

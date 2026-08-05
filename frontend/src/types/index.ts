// ========== 通用类型 ==========
export interface ApiResponse<T = any> {
  code: number
  data: T
  message?: string
  total?: number
  page?: number
  page_size?: number
  has_more?: boolean
  strategy?: string
}

// ========== 推荐系统类型 ==========
export interface Recommendation {
  relevance_score: number
  trending_score: number
  freshness_score: number
  composite_score: number
  match_dimensions: string[]
  match_reasons: string[]
  personalized: boolean
  /** 本次评分实际生效的权重（热度信号缺失时会动态再分配） */
  weights?: {
    personal: number
    trending: number
    freshness: number
  }
}

// ========== Feed 混合内容类型 ==========
export type FeedItemType = 'news' | 'product' | 'nearby'

export interface FeedItem {
  id: string | number
  _recommendation?: Recommendation
  // Common fields
  title?: string
  name?: string
  summary?: string
  image?: string
  icon?: string
  category?: string
  tags?: string[]
  // Type-specific
  published_at?: string
  source?: string
  read_count?: number
  trending?: boolean
  lowest_price?: number
  lowest_store?: string
  distance?: number
  address?: string
  rating?: number
}

// ========== 用户画像类型 ==========
export interface DimensionStatus {
  key: string
  name: string
  icon: string
  tier: 'core' | 'important' | 'auxiliary' | 'reference'
  weight: number
  active: boolean
}

export interface DimensionSummary extends DimensionStatus {
  weight_pct: string
  fields_count: number
  highlights: string[]
}

export interface ProfileSummary {
  dimensions: DimensionSummary[]
  total_weight: number
  activated_count: number
}

// ========== 快捷画像编辑 (interests 顶层字段) ==========
export interface LearningGoal {
  topic: string
  priority: 'high' | 'medium' | 'low'
}

export interface TrackingTopic {
  keyword: string
  weight: number
}

export interface Hobby {
  name: string
  frequency: 'daily' | 'weekly' | 'monthly' | 'occasionally'
  category: string
}

export interface InterestsFields {
  learning_goals: LearningGoal[]
  tracking_topics: TrackingTopic[]
  excluded_topics: string[]
  hobbies: Hobby[]
}

// ========== 天气类型 ==========
export interface CurrentWeather {
  temperature: number
  feels_like: number
  humidity: number
  condition: string
  icon: string
  wind_speed: number
  wind_direction: string
  uv_index: number
  visibility: number
  aqi: number
  aqi_level: string
}

export interface ForecastDay {
  day: string
  high: number
  low: number
  condition: string
  icon: string
  rain_prob: number
}

export interface WeatherAlert {
  level: string
  type: string
  message: string
}

// ========== 比价类型 ==========
export interface PriceCategory {
  id: string
  name: string
  icon: string
}

export interface Store {
  id: string
  name: string
  logo: string
  delivery_fee: number
  min_order: number
}

export interface ProductPrice {
  store_id: string
  price: number
  original: number
  in_stock: boolean
  promotion: string | null
  store?: Store
}

export interface PriceProduct {
  id: number
  name: string
  category: string
  image: string
  unit: string
  prices: ProductPrice[]
  trend: 'up' | 'down' | 'stable'
  trend_pct: number
  lowest_store: string
  lowest_price: number
  _recommendation?: Recommendation
}

export interface PriceAlert {
  id: number
  product: string
  target_price: number
  current_best: number
  store: string
  status: string
}

// ========== 周边资源类型 ==========
export interface NearbyCategory {
  id: string
  name: string
  icon: string
}

export interface NearbyResource {
  id: number
  name: string
  category: string
  icon: string
  distance: number
  address: string
  rating: number
  review_count: number
  open_status: string
  hours: string
  tags: string[]
  phone: string | null
  features: string[]
  lat?: number
  lng?: number
  source?: string
  _recommendation?: Recommendation
}

// ========== 新闻类型 ==========
export interface NewsCategory {
  id: string
  name: string
  icon: string
}

export interface NewsArticle {
  // RSS 文章使用 link 的 md5 全串（string）；mock 数据仍为 number
  id: string | number
  category: string
  title: string
  summary: string
  source: string
  author: string
  published_at: string
  image: string
  tags: string[]
  read_count: number
  trending: boolean
  link?: string
  _recommendation?: Recommendation
}

export interface HotTag {
  name: string
  count: number
}

// ========== 仪表盘类型 ==========
export interface DashboardStats {
  price_saved_today: number
  price_saved_this_month: number
  nearby_places: number
  unread_news: number
  active_alerts: number
}

export interface QuickAction {
  id: string
  name: string
  icon: string
  color: string
}

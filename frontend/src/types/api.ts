export interface UserRead {
  id: string
  email: string
  username: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
}

export interface Token {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface ProjectRead {
  id: string
  owner_id: string
  title: string
  description: string | null
  genre: string | null
  themes: string | null
  status: "draft" | "in_production" | "completed" | "archived"
  created_at: string
  updated_at: string
}

export interface ProjectList {
  items: ProjectRead[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface SeriesBibleRead {
  id: string
  project_id: string
  premise: string | null
  main_plot: string | null
  subplots: string | null
  character_relationships: string | null
  world_settings: string | null
  tone_and_style: string | null
  visual_style: string | null
  ending_direction: string | null
  episode_structure: string | null
  created_at: string
  updated_at: string
}

export interface CharacterRead {
  id: string
  project_id: string
  name: string
  role: string | null
  physical_appearance: string | null
  personality: string | null
  background: string | null
  costume: string | null
  reference_images: string | null
  consistency_instructions: string | null
  display_order: number
  created_at: string
  updated_at: string
}

export interface LocationRead {
  id: string
  project_id: string
  name: string
  description: string | null
  environment: string | null
  visual_references: string | null
  lighting: string | null
  atmosphere: string | null
  consistency_instructions: string | null
  display_order: number
  created_at: string
  updated_at: string
}

export interface EpisodeRead {
  id: string
  project_id: string
  episode_number: number
  title: string | null
  synopsis: string | null
  status: "planned" | "writing" | "scenes_done" | "prompts_ready" | "assets_generating" | "assets_ready" | "editing" | "completed"
  estimated_duration: number | null
  actual_duration: number | null
  production_cost: number | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface EpisodeList {
  items: EpisodeRead[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface SceneCharacterRead {
  id: string
  scene_id: string
  character_id: string
  role_in_scene: string | null
  notes: string | null
  character?: CharacterRead
}

export interface SceneRead {
  id: string
  episode_id: string
  location_id: string | null
  scene_number: number
  title: string | null
  description: string | null
  action: string | null
  camera_directions: string | null
  status: "planned" | "writing" | "prompts_ready" | "assets_generating" | "assets_ready" | "completed"
  estimated_duration: number | null
  created_at: string
  updated_at: string
  characters: SceneCharacterRead[]
}

export interface DialogueRead {
  id: string
  scene_id: string
  character_id: string
  order_index: number
  dialogue_text: string
  parenthetical: string | null
  audio_prompt: string | null
  created_at: string
  updated_at: string
  character?: CharacterRead
}

export type PromptType =
  | "character_image"
  | "location_image"
  | "scene_image"
  | "video_generation"
  | "camera_movement"
  | "character_action"
  | "dialogue_audio"
  | "background_music"
  | "sound_effect"
  | "subtitle"

export interface PromptRead {
  id: string
  project_id: string
  episode_id: string | null
  scene_id: string | null
  character_id: string | null
  location_id: string | null
  prompt_type: PromptType
  prompt_text: string
  negative_prompt: string | null
  parameters: string | null
  generated_result: string | null
  status: string
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface PromptList {
  items: PromptRead[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type AssetType =
  | "character_image"
  | "location_image"
  | "scene_image"
  | "video_clip"
  | "audio_clip"
  | "background_music"
  | "sound_effect"
  | "subtitle_file"
  | "final_episode"
  | "thumbnail"
  | "reference"

export type AssetStatus = "pending" | "uploading" | "ready" | "failed"

export interface AssetRead {
  id: string
  project_id: string
  episode_id: string | null
  scene_id: string | null
  prompt_id: string | null
  asset_type: AssetType
  file_name: string
  file_path: string
  file_size: number | null
  mime_type: string | null
  duration: number | null
  width: number | null
  height: number | null
  status: AssetStatus
  metadata: string | null
  created_at: string
  updated_at: string
}

export interface AssetList {
  items: AssetRead[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface GoogleAccountRead {
  id: string
  user_id: string
  email: string
  display_name: string | null
  is_active: boolean
  account_index: number
  scopes: string | null
  last_used_at: string | null
  created_at: string
  updated_at: string
}

export interface GoogleAccountList {
  items: GoogleAccountRead[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type FlowTaskType =
  | "image_generation"
  | "video_generation"
  | "prompt_preparation"
  | "asset_organization"

export type FlowTaskStatus =
  | "pending"
  | "ready_for_flow"
  | "in_progress"
  | "completed"
  | "failed"
  | "imported"

export interface FlowBridgeRead {
  id: string
  project_id: string
  episode_id: string | null
  scene_id: string | null
  google_account_id: string | null
  task_type: FlowTaskType
  status: FlowTaskStatus
  title: string
  description: string | null
  input_prompts: string | null
  reference_assets: string | null
  flow_url: string | null
  output_assets: string | null
  notes: string | null
  error_message: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface FlowBridgeList {
  items: FlowBridgeRead[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type StoryGenerationType =
  | "story_idea"
  | "episode_outline"
  | "full_series"
  | "scene_breakdown"
  | "dialogue_generation"
  | "character_development"
  | "conflict_development"
  | "cliffhanger"

export type StoryGenerationStatus =
  | "pending"
  | "generating"
  | "completed"
  | "failed"

export interface StoryEngineRead {
  id: string
  project_id: string
  episode_id: string | null
  scene_id: string | null
  generation_type: StoryGenerationType
  status: StoryGenerationStatus
  input_prompt: string | null
  input_context: string | null
  generated_output: string | null
  model_used: string | null
  tokens_used: number | null
  error_message: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface StoryEngineList {
  items: StoryEngineRead[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
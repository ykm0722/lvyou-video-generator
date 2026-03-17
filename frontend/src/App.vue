<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCamera, Upload, Document, Picture, MagicStick, Edit } from '@element-plus/icons-vue'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const step = ref(0)
const loading = ref(false)
const pdfFile = ref<File | null>(null)
const imageFile = ref<File | null>(null)
const travelInfo = ref<any>({})
const copyData = ref<any>({ title: '', points: [] })
const images = ref<any[]>([])
const script = ref<any>({ scenes: [] })
const videoPath = ref('')

const handlePdfChange = (file: any) => {
  pdfFile.value = file.raw
  return false
}

const handleImageChange = (file: any) => {
  imageFile.value = file.raw
  return false
}

const handleUpload = async () => {
  if (!pdfFile.value) return
  loading.value = true
  try {
    // 1. 上传PDF
    const formData = new FormData()
    formData.append('file', pdfFile.value)
    const uploadRes = await fetch(`${API_BASE_URL}/api/upload`, { method: 'POST', body: formData })
    const uploadData = await uploadRes.json()

    // 2. 解析PDF
    const parseRes = await fetch(`${API_BASE_URL}/api/parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filepath: uploadData.path })
    })
    travelInfo.value = await parseRes.json()

    // 3. 生成文案
    const copyRes = await fetch(`${API_BASE_URL}/api/copywriter/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(travelInfo.value)
    })
    copyData.value = await copyRes.json()

    // 4. 搜索图片 - 为每个景点单独搜索
    const highlights = travelInfo.value.highlights || []
    const destination = travelInfo.value.destination || 'travel'

    // 为每个景点搜索图片（最多6个景点，每个2张）
    const imagePromises = highlights.slice(0, 6).map((spot: string) =>
      fetch(`${API_BASE_URL}/api/images/search?keyword=${encodeURIComponent(spot + ' ' + destination)}&count=2`)
        .then(r => r.json())
        .catch(() => ({ images: [] }))
    )
    const imageResults = await Promise.all(imagePromises)
    images.value = imageResults.flatMap(r => r.images || [])

    console.log('搜索到的图片数量:', images.value.length)
    if (images.value.length === 0) {
      ElMessage.warning('未找到图片，使用默认图片')
      images.value = [{url: 'https://via.placeholder.com/1080x1920', thumb: 'https://via.placeholder.com/200x300'}]
    }

    // 5. 生成脚本
    const scriptRes = await fetch(`${API_BASE_URL}/api/script/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ travel_info: travelInfo.value, copy_data: copyData.value })
    })
    script.value = await scriptRes.json()

    step.value = 1
  } catch (error: any) {
    ElMessage.error('处理失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const handleGenerateVideo = async () => {
  loading.value = true
  try {
    const videoRes = await fetch(`${API_BASE_URL}/api/video/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        script: script.value,
        images: images.value,
        copyData: copyData.value,
        travelInfo: travelInfo.value
      })
    })
    const videoData = await videoRes.json()
    videoPath.value = videoData.path
    step.value = 2
    ElMessage.success('视频生成成功！')
  } catch (error: any) {
    ElMessage.error('视频生成失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const downloadVideo = () => {
  const link = document.createElement('a')
  link.href = API_BASE_URL + videoPath.value
  link.download = 'promo_video.mp4'
  link.click()
}
</script>

<template>
  <div id="app">
    <el-container>
      <el-header style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; height: 80px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
        <div style="display: flex; align-items: center; gap: 12px;">
          <el-icon :size="32"><VideoCamera /></el-icon>
          <h1 style="margin: 0; font-size: 28px; font-weight: 600; letter-spacing: -0.5px;">旅游推广视频生成平台</h1>
        </div>
      </el-header>

      <el-main style="background: linear-gradient(180deg, #f8f9ff 0%, #f0f2f5 100%); min-height: calc(100vh - 80px); padding: 60px 20px;">
        <div style="max-width: 1200px; margin: 0 auto;">

          <el-steps :active="step" align-center style="margin-bottom: 50px; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <el-step title="上传素材" />
            <el-step title="编辑内容" />
            <el-step title="生成视频" />
          </el-steps>

          <!-- 步骤1: 上传素材 -->
          <el-card v-if="step === 0" shadow="never" style="border-radius: 16px; border: none;">
            <template #header>
              <div style="display: flex; align-items: center; padding: 10px 0;">
                <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 16px;">
                  <el-icon :size="24" color="white"><Upload /></el-icon>
                </div>
                <div>
                  <div style="font-size: 20px; font-weight: 600; color: #1f2937;">上传素材</div>
                  <div style="font-size: 14px; color: #6b7280; margin-top: 4px;">上传PDF行程和宣传图片，AI将自动生成推广内容</div>
                </div>
              </div>
            </template>

            <el-row :gutter="24" style="margin-top: 20px;">
              <el-col :span="12">
                <el-upload
                  drag
                  :auto-upload="false"
                  :on-change="handlePdfChange"
                  accept=".pdf"
                  :limit="1">
                  <div style="padding: 40px 20px;">
                    <el-icon :size="64" color="#667eea" style="margin-bottom: 16px;"><Document /></el-icon>
                    <div style="font-size: 16px; color: #374151; font-weight: 500; margin-bottom: 8px;">上传PDF行程文件</div>
                    <div style="font-size: 13px; color: #9ca3af;">点击或拖拽文件到此处</div>
                  </div>
                </el-upload>
              </el-col>

              <el-col :span="12">
                <el-upload
                  drag
                  :auto-upload="false"
                  :on-change="handleImageChange"
                  accept="image/*"
                  :limit="1">
                  <div style="padding: 40px 20px;">
                    <el-icon :size="64" color="#10b981" style="margin-bottom: 16px;"><Picture /></el-icon>
                    <div style="font-size: 16px; color: #374151; font-weight: 500; margin-bottom: 8px;">上传宣传图片</div>
                    <div style="font-size: 13px; color: #9ca3af;">支持JPG、PNG格式</div>
                  </div>
                </el-upload>
              </el-col>
            </el-row>

            <div style="text-align: center; margin-top: 40px;">
              <el-button
                type="primary"
                size="large"
                @click="handleUpload"
                :loading="loading"
                :disabled="!pdfFile"
                style="padding: 16px 48px; font-size: 16px; font-weight: 500; border-radius: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none;">
                <el-icon style="margin-right: 8px;"><MagicStick /></el-icon>
                开始智能处理
              </el-button>
            </div>
          </el-card>

          <!-- 步骤2: 编辑内容 -->
          <div v-if="step === 1">
            <el-card shadow="never" style="margin-bottom: 24px; border-radius: 16px; border: none;">
              <template #header>
                <div style="display: flex; align-items: center;">
                  <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; margin-right: 12px;">
                    <el-icon :size="20" color="white"><Edit /></el-icon>
                  </div>
                  <span style="font-size: 18px; font-weight: 600; color: #1f2937;">AI生成文案</span>
                </div>
              </template>
              <el-form label-width="80px">
                <el-form-item label="标题">
                  <el-input v-model="copyData.title" size="large" />
                </el-form-item>
                <el-form-item label="卖点">
                  <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                    <el-tag v-for="(point, i) in copyData.points" :key="i" size="large" type="success">{{ point }}</el-tag>
                  </div>
                </el-form-item>
              </el-form>
            </el-card>

            <el-card shadow="never" style="margin-bottom: 24px; border-radius: 16px; border: none;">
              <template #header>
                <div style="display: flex; align-items: center;">
                  <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; margin-right: 12px;">
                    <el-icon :size="20" color="white"><Picture /></el-icon>
                  </div>
                  <span style="font-size: 18px; font-weight: 600; color: #1f2937;">高清图片素材</span>
                </div>
              </template>
              <el-row :gutter="16">
                <el-col :span="4" v-for="(img, i) in images" :key="i">
                  <el-image :src="img.thumb" fit="cover" style="width: 100%; height: 140px; border-radius: 12px; cursor: pointer;" />
                </el-col>
              </el-row>
            </el-card>

            <el-card shadow="never" style="margin-bottom: 24px; border-radius: 16px; border: none;">
              <template #header>
                <div style="display: flex; align-items: center;">
                  <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; margin-right: 12px;">
                    <el-icon :size="20" color="white"><VideoCamera /></el-icon>
                  </div>
                  <span style="font-size: 18px; font-weight: 600; color: #1f2937;">分镜头脚本</span>
                </div>
              </template>
              <el-timeline>
                <el-timeline-item v-for="(scene, i) in script.scenes" :key="i" :timestamp="`场景${Number(i)+1} · ${scene.duration}秒`" placement="top">
                  <el-card shadow="never" style="background: #f9fafb; border: 1px solid #e5e7eb;">
                    <p style="margin: 0 0 8px 0; color: #6b7280;"><strong>画面:</strong> {{ scene.image_keyword }}</p>
                    <p style="margin: 0; color: #374151;"><strong>文案:</strong> {{ scene.text }}</p>
                  </el-card>
                </el-timeline-item>
              </el-timeline>
            </el-card>

            <div style="text-align: center; display: flex; gap: 16px; justify-content: center;">
              <el-button size="large" @click="step = 0">返回</el-button>
              <el-button type="primary" size="large" @click="handleGenerateVideo" :loading="loading" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none;">
                <el-icon style="margin-right: 8px;"><VideoCamera /></el-icon>
                生成视频
              </el-button>
            </div>
          </div>

          <!-- 步骤3: 生成视频 -->
          <el-card v-if="step === 2" shadow="never" style="text-align: center; border-radius: 16px; border: none; padding: 40px;">
            <div style="margin-bottom: 30px;">
              <h2 style="font-size: 24px; font-weight: 600; color: #1f2937; margin-bottom: 10px;">视频生成完成</h2>
              <p style="color: #6b7280;">预览视频，满意后可下载</p>
            </div>

            <div style="max-width: 600px; margin: 0 auto 30px;">
              <video :src="API_BASE_URL + videoPath" controls style="width: 100%; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);"></video>
            </div>

            <div style="display: flex; gap: 16px; justify-content: center;">
              <el-button size="large" @click="step = 1">重新生成</el-button>
              <el-button type="primary" size="large" @click="downloadVideo" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none;">
                下载视频
              </el-button>
              <el-button size="large" @click="step = 0">返回首页</el-button>
            </div>
          </el-card>

        </div>
      </el-main>
    </el-container>
  </div>
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
#app { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }
.el-upload-dragger:hover { border-color: #667eea; }
.el-image:hover { transform: scale(1.05); }
</style>

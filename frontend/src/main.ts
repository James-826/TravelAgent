import { createApp } from 'vue'
import Alert from 'ant-design-vue/es/alert'
import Button from 'ant-design-vue/es/button'
import Col from 'ant-design-vue/es/col'
import Collapse from 'ant-design-vue/es/collapse'
import DatePicker from 'ant-design-vue/es/date-picker'
import Form from 'ant-design-vue/es/form'
import Input from 'ant-design-vue/es/input'
import InputNumber from 'ant-design-vue/es/input-number'
import List from 'ant-design-vue/es/list'
import Progress from 'ant-design-vue/es/progress'
import Row from 'ant-design-vue/es/row'
import Segmented from 'ant-design-vue/es/segmented'
import Select from 'ant-design-vue/es/select'
import Space from 'ant-design-vue/es/space'
import Statistic from 'ant-design-vue/es/statistic'
import Steps from 'ant-design-vue/es/steps'
import Switch from 'ant-design-vue/es/switch'
import Tag from 'ant-design-vue/es/tag'
import Timeline from 'ant-design-vue/es/timeline'
import 'ant-design-vue/dist/reset.css'

import App from './App.vue'
import router from './router'
import './styles/main.css'

const app = createApp(App)

;[
  Alert,
  Button,
  Col,
  Collapse,
  DatePicker,
  Form,
  Input,
  InputNumber,
  List,
  Progress,
  Row,
  Segmented,
  Select,
  Space,
  Statistic,
  Steps,
  Switch,
  Tag,
  Timeline
].forEach((component) => app.use(component))

app.use(router).mount('#app')

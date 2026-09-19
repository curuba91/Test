import { HashRouter, Route, Routes, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Courses } from './pages/Courses'
import { ModulePage } from './pages/ModulePage'
import { LessonPage } from './pages/LessonPage'
import { QuizPage } from './pages/QuizPage'
import { ExamPage } from './pages/ExamPage'
import { Tools } from './pages/Tools'
import { DiveLog } from './pages/DiveLog'
import { Flashcards } from './pages/Flashcards'
import { Signals } from './pages/Signals'
import { Glossary } from './pages/Glossary'
import { Achievements } from './pages/Achievements'
import { Checklists } from './pages/Checklists'
import { Settings } from './pages/Settings'
import { useAchievementWatcher } from './hooks/useAchievements'

function Watcher() {
  useAchievementWatcher()
  return null
}

export default function App() {
  return (
    <HashRouter>
      <Watcher />
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="kurse" element={<Courses />} />
          <Route path="kurse/:moduleId" element={<ModulePage />} />
          <Route path="kurse/:moduleId/:lessonId" element={<LessonPage />} />
          <Route path="quiz/:moduleId" element={<QuizPage />} />
          <Route path="pruefung" element={<ExamPage />} />
          <Route path="rechner" element={<Tools />} />
          <Route path="logbuch" element={<DiveLog />} />
          <Route path="karteikarten" element={<Flashcards />} />
          <Route path="handzeichen" element={<Signals />} />
          <Route path="glossar" element={<Glossary />} />
          <Route path="erfolge" element={<Achievements />} />
          <Route path="checklisten" element={<Checklists />} />
          <Route path="einstellungen" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </HashRouter>
  )
}

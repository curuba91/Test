import type { CourseModule } from './types'
import { physik, physiologie } from './modules-1'
import { ausruestung, skills } from './modules-2'
import { planung, nitrox } from './modules-3'
import { navigation, meer, notfall } from './modules-4'

export const modules: CourseModule[] = [physik, physiologie, ausruestung, skills, planung, navigation, meer, nitrox, notfall]

export const allLessons = modules.flatMap((m) => m.lessons.map((l) => ({ ...l, moduleId: m.id })))

export function getModule(id: string) {
  return modules.find((m) => m.id === id)
}

export function getLesson(moduleId: string, lessonId: string) {
  return getModule(moduleId)?.lessons.find((l) => l.id === lessonId)
}
